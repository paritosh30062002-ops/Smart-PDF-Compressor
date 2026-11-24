"""Compressor page: the original compression tool + plan limits."""
import html
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import streamlit as st

from core import config, nav
from core.auth import current_user, invalidate_profile, profile_and_quota
from core.store import get_store
from core.ui import plan_badge, quota_summary, raw_html

# --- Session State Initialization ---
if "result_bundle" not in st.session_state:
    st.session_state.result_bundle = None
if "terminal_logs" not in st.session_state:
    st.session_state.terminal_logs = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark Glass"


def push_log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.terminal_logs.append({
        "ts": ts,
        "level": level.upper(),
        "msg": message,
    })


def clear_logs() -> None:
    st.session_state.terminal_logs = []


def reset_app() -> None:
    st.session_state.result_bundle = None
    st.session_state.terminal_logs = []
    st.session_state.uploader_key += 1


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def get_gs_binary() -> str | None:
    return shutil.which("gswin64c") or shutil.which("gs")


def get_preset_config(preset: str, custom_dpi: int) -> dict:
    if preset == "Light (Best Quality)":
        return {
            "pdf_settings": "/printer",
            "compat": "1.6",
            "dpi": custom_dpi if custom_dpi > 0 else 175,
            "downsample": True,
        }
    if preset == "Maximum (Smallest)":
        return {
            "pdf_settings": "/screen",
            "compat": "1.4",
            "dpi": custom_dpi if custom_dpi > 0 else 96,
            "downsample": True,
        }
    return {
        "pdf_settings": "/ebook",
        "compat": "1.4",
        "dpi": custom_dpi if custom_dpi > 0 else 130,
        "downsample": True,
    }


MAX_VISIBLE_LOGS = 250  # keeps every update light even for huge batches (counter still shows all events)


def render_glass_terminal(logs: list[dict]) -> None:
    if not logs:
        body_html = (
            '<div class="log-row log-row-INFO">'
            '<span class="log-ts">[--:--:--]</span>'
            '<span class="log-badge badge-INFO">INFO</span>'
            '<span class="log-msg">Ready. Upload ZIP or PDFs and start compression to stream live logs.</span>'
            '</div>'
        )
    else:
        lines = []
        hidden = len(logs) - MAX_VISIBLE_LOGS
        if hidden > 0:
            lines.append(f'<div class="log-row log-row-more">… {hidden} earlier events</div>')
        for entry in logs[-MAX_VISIBLE_LOGS:]:
            ts_e = html.escape(entry["ts"])
            lvl = entry["level"] if entry["level"] in {"INFO", "OK", "DONE", "WARN", "ERROR"} else "INFO"
            msg_e = html.escape(entry["msg"])
            lines.append(
                f'<div class="log-row log-row-{lvl}">'
                f'<span class="log-ts">[{ts_e}]</span>'
                f'<span class="log-badge badge-{lvl}">{lvl}</span>'
                f'<span class="log-msg">{msg_e}</span>'
                f'</div>'
            )
        body_html = "".join(lines)

    term_html = (
        f'<div class="glass-term-topbar">'
        f'<div class="glass-term-label"><span class="live-dot"></span>Live Terminal Logs</div>'
        f'<span class="live-pill">{len(logs)} EVENTS</span>'
        f'</div>'
        f'<div class="glass-terminal"><div class="term-scroll"><div class="term-inner">{body_html}</div></div></div>'
    )
    # st.html injects the HTML directly (no markdown parsing), which is much lighter per update.
    if hasattr(st, "html"):
        st.html(term_html)
    else:
        st.markdown(term_html, unsafe_allow_html=True)


def compress_single_pdf(
    pdf_path: Path,
    preset_cfg: dict,
    gs_bin: str,
    has_qpdf: bool,
    min_kb_skip: int,
) -> dict:
    orig_size = pdf_path.stat().st_size
    rel_label = pdf_path.name

    if orig_size == 0:
        return {
            "file": rel_label,
            "before": 0,
            "after": 0,
            "status": "skipped",
            "detail": "0-byte empty PDF",
        }

    try:
        with open(pdf_path, "rb") as f:
            header = f.read(8)
        if b"%PDF-" not in header:
            return {
                "file": rel_label,
                "before": orig_size,
                "after": orig_size,
                "status": "fallback",
                "detail": "Missing %PDF header (kept original)",
            }
    except OSError as exc:
        return {
            "file": rel_label,
            "before": orig_size,
            "after": orig_size,
            "status": "fallback",
            "detail": f"Read error: {exc}",
        }

    if min_kb_skip > 0 and orig_size < min_kb_skip * 1024:
        return {
            "file": rel_label,
            "before": orig_size,
            "after": orig_size,
            "status": "skipped",
            "detail": f"Smaller than {min_kb_skip} KB threshold",
        }

    temp_pdf = pdf_path.with_name(f"{pdf_path.name}.gs_tmp.pdf")
    qpdf_temp = pdf_path.with_name(f"{pdf_path.name}.qpdf_tmp.pdf")

    dpi = preset_cfg["dpi"]
    gs_cmd = [
        gs_bin,
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel={preset_cfg['compat']}",
        f"-dPDFSETTINGS={preset_cfg['pdf_settings']}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        f"-dDownsampleColorImages={str(preset_cfg['downsample']).lower()}",
        "-dColorImageDownsampleType=/Bicubic",
        f"-dColorImageResolution={dpi}",
        f"-dDownsampleGrayImages={str(preset_cfg['downsample']).lower()}",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-dGrayImageResolution={dpi}",
        f"-dDownsampleMonoImages={str(preset_cfg['downsample']).lower()}",
        "-dMonoImageDownsampleType=/Subsample",
        f"-dMonoImageResolution={max(dpi, 150)}",
        f"-sOutputFile={temp_pdf}",
        str(pdf_path),
    ]

    try:
        subprocess.run(gs_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if not temp_pdf.exists() or temp_pdf.stat().st_size == 0:
            return {
                "file": rel_label,
                "before": orig_size,
                "after": orig_size,
                "status": "fallback",
                "detail": "Ghostscript produced empty output",
            }

        candidate_path = temp_pdf
        if has_qpdf:
            qpdf_cmd = [
                "qpdf",
                "--empty",
                "--pages",
                str(temp_pdf),
                "--",
                "--object-streams=generate",
                "--compress-streams=y",
                "--recompress-flate",
                "--compression-level=9",
                str(qpdf_temp),
            ]
            try:
                subprocess.run(qpdf_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if qpdf_temp.exists() and qpdf_temp.stat().st_size > 0:
                    candidate_path = qpdf_temp
            except subprocess.CalledProcessError:
                candidate_path = temp_pdf

        new_size = candidate_path.stat().st_size
        if new_size < orig_size:
            shutil.move(str(candidate_path), str(pdf_path))
            saved_pct = ((orig_size - new_size) / orig_size) * 100
            return {
                "file": rel_label,
                "before": orig_size,
                "after": new_size,
                "status": "compressed",
                "detail": f"Saved {saved_pct:.1f}% ({dpi} DPI)",
            }

        return {
            "file": rel_label,
            "before": orig_size,
            "after": orig_size,
            "status": "kept",
            "detail": "Already optimal (kept original)",
        }

    except subprocess.CalledProcessError as exc:
        err_lines = exc.stderr.decode("utf-8", errors="ignore").strip().splitlines()
        reason = err_lines[-1][:90] if err_lines else "Ghostscript failed (possibly encrypted/corrupt)"
        return {
            "file": rel_label,
            "before": orig_size,
            "after": orig_size,
            "status": "fallback",
            "detail": f"Kept original — {reason}",
        }
    finally:
        for tmp in (temp_pdf, qpdf_temp):
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass


def export_pdfs_to_folder(
    pdf_paths: list[Path],
    staging_dir: Path,
    target_folder_str: str,
    preserve_subfolders: bool,
) -> tuple[list[str], str | None]:
    target_root = Path(target_folder_str.strip()).expanduser()
    try:
        target_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return [], f"Could not create output folder '{target_root}': {exc}"

    saved_paths: list[str] = []
    for src_pdf in pdf_paths:
        if not src_pdf.is_file():
            continue
        rel = src_pdf.relative_to(staging_dir)
        if preserve_subfolders:
            dest_file = target_root / rel
        else:
            dest_file = target_root / src_pdf.name
            if dest_file.exists():
                stem = dest_file.stem
                suffix = dest_file.suffix
                counter = 1
                while dest_file.exists():
                    dest_file = target_root / f"{stem}_{counter}{suffix}"
                    counter += 1

        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_pdf, dest_file)
            saved_paths.append(str(dest_file))
        except OSError as exc:
            return saved_paths, f"Failed writing '{dest_file}': {exc}"

    return saved_paths, None


gs_bin = get_gs_binary()
has_qpdf = bool(shutil.which("qpdf"))

if not gs_bin:
    st.error("Ghostscript (`gswin64c` or `gs`) was not found in your system `PATH`.")

# --- Account / plan limits ---
user = current_user()
if not user:
    st.switch_page(nav.page("login"))
profile, quota = profile_and_quota(user, force=True)
store = get_store()

q_info, q_reset = st.columns([6, 1], vertical_alignment="center")
with q_info:
    if quota is None:
        raw_html('<div class="quota-strip">Account service is not reachable right now. Please try again in a minute.</div>')
    else:
        limit_txt = quota_summary(quota)
        raw_html(f'<div class="quota-strip"><span>{plan_badge(quota.plan)}&nbsp; {limit_txt}</span></div>')
with q_reset:
    st.button("Reset", on_click=reset_app, use_container_width=True)

quota_blocked = quota is None or quota.files_left == 0 or quota.pdfs_left == 0

# --- Main Workspace: Left User Flow, Right Live Glass Terminal ---
left_col, right_col = st.columns([3.3, 2.0], gap="large")

with right_col:
    log_placeholder = st.empty()
    with log_placeholder.container():
        render_glass_terminal(st.session_state.terminal_logs)

with left_col:
    preset = st.radio(
        "Compression Preset",
        ["Balanced (Recommended)", "Maximum (Smallest)", "Light (Best Quality)"],
        horizontal=True,
    )

    uploaded_files = st.file_uploader(
        "Upload ZIP file(s) and/or loose PDF file(s)",
        type=["zip", "pdf"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        names_preview = ", ".join(html.escape(f.name) for f in uploaded_files[:4])
        extra_cnt = len(uploaded_files) - 4
        extra_txt = f" +{extra_cnt} more" if extra_cnt > 0 else ""
        st.markdown(
            f'<div class="glass-selection-strip"><strong>Selected Files ({len(uploaded_files)}):</strong> {names_preview}{html.escape(extra_txt)}</div>',
            unsafe_allow_html=True,
        )

    save_only_pdfs_to_folder = config.allow_folder_export() and st.checkbox(
        "Save only PDFs to a selected output folder",
        value=False,
    )
    output_folder_path = ""
    preserve_folder_tree = True
    if save_only_pdfs_to_folder:
        default_out = str(Path.home() / "Downloads" / "Compressed_PDFs")
        output_folder_path = st.text_input(
            "Output Folder Path",
            value=default_out,
            placeholder=r"e.g. D:\Compressed_PDFs or /home/user/compressed_pdfs",
        )
        preserve_folder_tree = st.checkbox(
            "Keep subfolder structure inside output folder",
            value=True,
        )
        if output_folder_path.strip():
            st.markdown(
                f'<div class="glass-selection-strip"><strong>Target PDF Folder:</strong> {html.escape(output_folder_path.strip())}</div>',
                unsafe_allow_html=True,
            )

    with st.expander("Advanced Options"):
        adv_c1, adv_c2 = st.columns(2)
        with adv_c1:
            auto_workers = min(8, os.cpu_count() or 4)
            workers = st.slider("Parallel Workers", min_value=1, max_value=16, value=auto_workers)
            min_kb_skip = st.number_input("Skip PDFs smaller than (KB)", min_value=0, max_value=10000, value=25, step=5)
            max_uncompressed_mb = st.number_input("Max uncompressed archive size (MB)", min_value=50, max_value=5000, value=1024, step=50)
        with adv_c2:
            custom_dpi = st.slider("Custom Target DPI (0 = Preset Default)", min_value=0, max_value=240, value=0, step=10)
            keep_non_pdf = st.checkbox("Keep non-PDF files in output ZIP", value=True)
            only_pdfs_in_zip = st.checkbox("Include only PDFs inside output ZIP", value=False)

    start_clicked = st.button(
        "Start Compression",
        type="primary",
        disabled=(not uploaded_files or not gs_bin or quota_blocked),
        use_container_width=True,
    )

    if quota is not None and quota_blocked:
        st.info("Your plan limit is used up. Upgrade on the Pricing page, or come back tomorrow on the Free plan.")
        st.page_link(nav.page("pricing"), label="See Pro plans", icon=":material/workspace_premium:")

    progress_bar = st.progress(0.0)
    timing_placeholder = st.empty()


_LOG_SYNC_MIN_INTERVAL = 0.08  # seconds; batches bursts of results into ~12 smooth UI updates per second
_log_sync_state = {"last": 0.0}


def sync_live_logs() -> None:
    logs = st.session_state.terminal_logs
    now = time.perf_counter()
    # Important events (and the first few) always render immediately; bursts of per-file
    # results are batched so the browser isn't asked to repaint dozens of times per second.
    urgent = len(logs) <= 3 or logs[-1]["level"] in {"DONE", "ERROR", "WARN"}
    if not urgent and now - _log_sync_state["last"] < _LOG_SYNC_MIN_INTERVAL:
        return
    _log_sync_state["last"] = now
    with log_placeholder.container():
        render_glass_terminal(logs)


# --- Execution Pipeline ---
if start_clicked and uploaded_files and gs_bin:
    if save_only_pdfs_to_folder and not output_folder_path.strip():
        st.error("Please enter a valid output folder path or uncheck 'Save only PDFs to a selected output folder'.")
        st.stop()

    upload_err = quota.check_upload(len(uploaded_files)) if quota else "Account service is not reachable right now."
    if upload_err:
        st.error(upload_err)
        st.stop()

    st.session_state.result_bundle = None
    clear_logs()

    preset_cfg = get_preset_config(preset, custom_dpi)
    push_log(
        "INFO",
        f"Started job: preset='{preset}', DPI={preset_cfg['dpi']}, workers={workers}, qpdf={'yes' if has_qpdf else 'no'}.",
    )
    sync_live_logs()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        staging_dir = temp_root / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)

        zip_inputs = [f for f in uploaded_files if f.name.lower().endswith(".zip")]
        pdf_inputs = [f for f in uploaded_files if f.name.lower().endswith(".pdf")]

        uncompressed_total = 0
        for zf_upload in zip_inputs:
            z_path = temp_root / zf_upload.name
            z_path.write_bytes(zf_upload.getvalue())
            try:
                with zipfile.ZipFile(z_path, "r") as zf:
                    for info in zf.infolist():
                        if not info.is_dir():
                            uncompressed_total += info.file_size
            except zipfile.BadZipFile:
                push_log("WARN", f"Skipped invalid ZIP file: {zf_upload.name}")
                sync_live_logs()
                continue

            if uncompressed_total > max_uncompressed_mb * 1024 * 1024:
                st.error(f"Uncompressed archive size exceeds {max_uncompressed_mb} MB limit.")
                push_log("ERROR", f"Aborted: uncompressed size exceeded {max_uncompressed_mb} MB guardrail.")
                sync_live_logs()
                st.stop()

            extract_target = staging_dir / Path(zf_upload.name).stem
            extract_target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(z_path, "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    target_file = (extract_target / member.filename).resolve()
                    if not str(target_file).startswith(str(extract_target.resolve())):
                        push_log("WARN", f"Blocked unsafe path inside ZIP: {member.filename}")
                        sync_live_logs()
                        continue
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, "r") as src, open(target_file, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            push_log("INFO", f"Extracted '{zf_upload.name}'.")
            sync_live_logs()

        if pdf_inputs:
            loose_dir = staging_dir / "loose_pdfs"
            loose_dir.mkdir(parents=True, exist_ok=True)
            for pf_upload in pdf_inputs:
                out_p = loose_dir / Path(pf_upload.name).name
                out_p.write_bytes(pf_upload.getvalue())
            push_log("INFO", f"Added {len(pdf_inputs)} loose PDF file(s) to queue.")
            sync_live_logs()

        pdf_files = [
            p for p in staging_dir.rglob("*")
            if p.is_file() and p.suffix.lower() == ".pdf"
        ]

        if not pdf_files:
            push_log("WARN", "No PDF files found in uploaded files.")
            sync_live_logs()
            st.warning("No PDF files were found to compress.")
        else:
            pdf_err = quota.check_pdfs(len(pdf_files))
            if pdf_err:
                push_log("ERROR", pdf_err)
                sync_live_logs()
                st.error(pdf_err)
                st.stop()

            total_files = len(pdf_files)
            push_log("INFO", f"Found {total_files} PDF(s). Compressing with {workers} parallel workers...")
            sync_live_logs()

            start_time = time.perf_counter()
            completed = 0
            records = []
            total_before = 0
            total_after = 0

            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(compress_single_pdf, pdf_path, preset_cfg, gs_bin, has_qpdf, min_kb_skip): pdf_path
                    for pdf_path in pdf_files
                }

                for future in as_completed(future_map):
                    pdf_path = future_map[future]
                    res = future.result()
                    rel_name = str(pdf_path.relative_to(staging_dir))
                    res["file"] = rel_name
                    records.append(res)

                    total_before += res["before"]
                    total_after += res["after"]
                    completed += 1

                    elapsed = time.perf_counter() - start_time
                    avg_per_item = elapsed / completed
                    eta = avg_per_item * (total_files - completed)

                    pct = completed / total_files
                    progress_bar.progress(pct)
                    timing_placeholder.caption(
                        f"Progress: **{completed}/{total_files}** ({pct * 100:.0f}%)  |  "
                        f"Elapsed: **{format_duration(elapsed)}**  |  "
                        f"ETA: **{format_duration(eta)}**"
                    )

                    lvl = "OK" if res["status"] == "compressed" else ("WARN" if res["status"] == "fallback" else "INFO")
                    push_log(
                        lvl,
                        f"[{completed}/{total_files}] {rel_name}: {res['before'] / 1024:.1f} KB -> {res['after'] / 1024:.1f} KB ({res['detail']})",
                    )
                    sync_live_logs()

            saved_folder_files: list[str] = []
            folder_err: str | None = None
            if save_only_pdfs_to_folder:
                saved_folder_files, folder_err = export_pdfs_to_folder(
                    pdf_paths=pdf_files,
                    staging_dir=staging_dir,
                    target_folder_str=output_folder_path,
                    preserve_subfolders=preserve_folder_tree,
                )
                if folder_err:
                    push_log("ERROR", folder_err)
                else:
                    push_log("OK", f"Saved {len(saved_folder_files)} PDF(s) to '{output_folder_path.strip()}'.")
                sync_live_logs()

            out_zip_path = temp_root / "compressed_output.zip"
            included_count = 0
            with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf_out:
                for file_path in sorted(staging_dir.rglob("*")):
                    if not file_path.is_file():
                        continue
                    is_pdf = file_path.suffix.lower() == ".pdf"
                    if only_pdfs_in_zip and not is_pdf:
                        continue
                    if not keep_non_pdf and not is_pdf:
                        continue
                    arcname = str(file_path.relative_to(staging_dir))
                    zf_out.write(file_path, arcname)
                    included_count += 1

            total_elapsed = time.perf_counter() - start_time
            saved_bytes = total_before - total_after
            saved_mb = saved_bytes / (1024 * 1024)
            saved_pct = (saved_bytes / total_before * 100) if total_before > 0 else 0.0

            if len(zip_inputs) == 1 and not pdf_inputs:
                out_filename = f"{Path(zip_inputs[0].name).stem}_compressed.zip"
            else:
                out_filename = f"pdfs_compressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            counts = {
                "compressed": sum(1 for r in records if r["status"] == "compressed"),
                "kept": sum(1 for r in records if r["status"] == "kept"),
                "skipped": sum(1 for r in records if r["status"] == "skipped"),
                "fallback": sum(1 for r in records if r["status"] == "fallback"),
            }

            summary_text = (
                f"PDF Compression Summary ({preset}, {preset_cfg['dpi']} DPI)\n"
                f"- Files scanned: {total_files} | Compressed: {counts['compressed']} | "
                f"Kept optimal: {counts['kept']} | Skipped: {counts['skipped']} | Fallback: {counts['fallback']}\n"
                f"- Before: {total_before / (1024 * 1024):.2f} MB -> After: {total_after / (1024 * 1024):.2f} MB\n"
                f"- Total saved: {saved_mb:.2f} MB ({saved_pct:.1f}%) in {format_duration(total_elapsed)}"
            )
            if save_only_pdfs_to_folder and not folder_err:
                summary_text += f"\n- Saved {len(saved_folder_files)} PDFs to folder: {output_folder_path.strip()}"

            push_log(
                "DONE",
                f"Completed in {format_duration(total_elapsed)}. Saved {saved_mb:.2f} MB ({saved_pct:.1f}%). Packed {included_count} ZIP items.",
            )
            sync_live_logs()

            st.session_state.result_bundle = {
                "zip_bytes": out_zip_path.read_bytes(),
                "filename": out_filename,
                "before_mb": total_before / (1024 * 1024),
                "after_mb": total_after / (1024 * 1024),
                "saved_mb": saved_mb,
                "saved_pct": saved_pct,
                "elapsed_str": format_duration(total_elapsed),
                "counts": counts,
                "records": sorted(records, key=lambda x: x["file"].lower()),
                "summary_text": summary_text,
                "saved_folder_files": saved_folder_files,
                "folder_err": folder_err,
                "target_folder": output_folder_path.strip() if save_only_pdfs_to_folder else "",
            }

            try:
                store.add_usage(user["email"], len(uploaded_files), total_files, total_before, total_after)
            except Exception:
                push_log("WARN", "Compression done, but usage could not be saved to your account.")
                sync_live_logs()
            invalidate_profile()
            st.rerun()  # refresh the plan/usage strip; results stay (they live in session_state)

# --- Persistent Results View ---
bundle = st.session_state.result_bundle
if bundle:
    st.divider()
    st.success(f"Compression finished in **{bundle['elapsed_str']}**.")

    if bundle["folder_err"]:
        st.warning(bundle["folder_err"])
    elif bundle["target_folder"]:
        st.info(f"Saved **{len(bundle['saved_folder_files'])}** PDF file(s) to: `{bundle['target_folder']}`")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Original PDF Size", f"{bundle['before_mb']:.2f} MB")
    m2.metric("Compressed PDF Size", f"{bundle['after_mb']:.2f} MB")
    m3.metric("Space Saved", f"{bundle['saved_mb']:.2f} MB", f"-{bundle['saved_pct']:.1f}%")
    m4.metric("PDFs Compressed", f"{bundle['counts']['compressed']} / {len(bundle['records'])}")

    st.download_button(
        label=f"Download {bundle['filename']}",
        data=bundle["zip_bytes"],
        file_name=bundle["filename"],
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )

    with st.expander("Copyable Summary Report"):
        st.code(bundle["summary_text"], language="text")

    with st.expander("Per-File Breakdown"):
        table_rows = [
            {
                "File": r["file"],
                "Before (KB)": round(r["before"] / 1024, 1),
                "After (KB)": round(r["after"] / 1024, 1),
                "Status": r["status"],
                "Notes": r["detail"],
            }
            for r in bundle["records"]
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

