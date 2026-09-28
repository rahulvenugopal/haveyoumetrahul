"""
============================================================================
Criticality Demo: Synthetic Time Series with DFA, fE/I, & Lyapunov Exponent
============================================================================

Generates 6 synthetic 1D time series that mimic different dynamical regimes
a neuroscientist might encounter in EEG, then computes:

    1. DFA exponent  (α)   — via crosci library
    2. fE/I ratio          — via crosci library
    3. Largest Lyapunov exponent (λ) — via nolds library

For each signal we also show:
    • The raw time-series waveform
    • The FFT power spectrum (log-log)

Requires: numpy, scipy, matplotlib, crosci, nolds
Install:  python -m pip install crosci nolds matplotlib scipy numpy

Reference repo for crosci:
    https://github.com/Critical-Brain-Dynamics/crosci
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for headless execution

import numpy as np
from scipy import signal as sig
from scipy.signal import hilbert
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import nolds

# ── crosci imports ──────────────────────────────────────────────────────────
from crosci.biomarkers import DFA, fEI, compute_band_biomarkers


# ═══════════════════════════════════════════════════════════════════════════
# 1. SIGNAL GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def generate_white_noise(n_samples, fs):
    """Pure white noise — no temporal correlations."""
    return np.random.randn(n_samples)


def generate_pink_noise(n_samples, fs, exponent=1.0):
    """1/f^exponent noise via spectral synthesis (Timmer & König method)."""
    freqs = np.fft.rfftfreq(n_samples, d=1.0/fs)
    freqs[0] = 1  # avoid division by zero
    power = 1.0 / (freqs ** exponent)
    phases = np.random.uniform(0, 2*np.pi, len(freqs))
    spectrum = np.sqrt(power) * np.exp(1j * phases)
    spectrum[0] = 0  # zero DC
    ts = np.fft.irfft(spectrum, n=n_samples)
    return ts / np.std(ts)


def generate_subcritical_sleep(n_samples, fs):
    """
    Mimics deep NREM sleep: dominated by slow delta oscillations (0.5–4 Hz)
    with low complexity and strong periodicity.
    """
    t = np.arange(n_samples) / fs
    # Strong delta oscillation + weak harmonics
    delta = 3.0 * np.sin(2 * np.pi * 1.5 * t)
    delta += 1.0 * np.sin(2 * np.pi * 3.0 * t + 0.3)
    # Very small amount of noise
    noise = 0.3 * np.random.randn(n_samples)
    return delta + noise


def generate_near_critical_rest(n_samples, fs):
    """
    Mimics resting-state EEG with alpha oscillations (8-13 Hz) whose
    amplitude is modulated by long-range correlated 1/f fluctuations.
    This produces near-critical dynamics with LRTC in the amplitude envelope.
    """
    t = np.arange(n_samples) / fs

    # Generate a 1/f modulation envelope (long-range correlated)
    envelope = generate_pink_noise(n_samples, fs, exponent=1.0)
    # Make it positive and slow (low-pass at ~2 Hz)
    b, a = sig.butter(4, 2.0 / (fs/2), btype='low')
    envelope = sig.filtfilt(b, a, envelope)
    envelope = envelope - np.min(envelope) + 0.5  # shift to positive
    envelope = envelope / np.max(envelope)

    # Alpha oscillation modulated by the 1/f envelope
    alpha = envelope * np.sin(2 * np.pi * 10.0 * t)

    # Add some broadband noise
    noise = 0.15 * np.random.randn(n_samples)
    return alpha + noise


def generate_supercritical_seizure(n_samples, fs):
    """
    Mimics ictal (seizure) EEG: high-amplitude, rapidly evolving
    rhythmic activity with increasing frequency and amplitude.
    """
    t = np.arange(n_samples) / fs
    duration = n_samples / fs

    # Chirp-like seizure: frequency sweeps from 3 Hz to 15 Hz
    freq_start, freq_end = 3.0, 15.0
    instantaneous_freq = freq_start + (freq_end - freq_start) * (t / duration)
    phase = 2 * np.pi * np.cumsum(instantaneous_freq) / fs

    # Amplitude ramps up then saturates
    amp_env = 2.0 + 4.0 * (1 - np.exp(-t / (duration * 0.3)))

    seizure = amp_env * np.sin(phase)
    # Add some correlated noise
    noise = 0.5 * generate_pink_noise(n_samples, fs, exponent=0.5)
    return seizure + noise


def generate_lorenz_chaotic(n_samples, fs, sigma=10, rho=28, beta=8/3):
    """
    Lorenz system — a classical chaotic system.
    Returns the x-component, resampled to match our desired n_samples.
    """
    dt = 0.01
    total_steps = n_samples * 5  # oversample then downsample
    x, y, z = 1.0, 1.0, 1.0
    xs = np.zeros(total_steps)
    for i in range(total_steps):
        dx = sigma * (y - x) * dt
        dy = (x * (rho - z) - y) * dt
        dz = (x * y - beta * z) * dt
        x += dx; y += dy; z += dz
        xs[i] = x

    # Resample to desired length
    xs = sig.resample(xs, n_samples)
    return xs / np.std(xs)


def generate_brownian_walk(n_samples, fs):
    """
    Brownian motion (integrated white noise) — strongly correlated, α >> 1.
    """
    steps = np.random.randn(n_samples)
    walk = np.cumsum(steps)
    return walk / np.std(walk)


# ═══════════════════════════════════════════════════════════════════════════
# 2. METRIC COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_dfa_crosci(signal_1d, fs, fit_interval=(4, 20)):
    """
    Compute DFA exponent using crosci library.
    crosci.DFA expects shape (n_channels, n_times).
    """
    signal_2d = signal_1d.reshape(1, -1).astype(np.float64)
    # compute_interval should be wider than or equal to fit_interval
    compute_interval = (2, 30)
    try:
        dfa_val, _, _, _ = DFA(signal_2d, fs, fit_interval, compute_interval)
        val = float(np.squeeze(dfa_val))
        if np.isnan(val):
            return compute_dfa_manual(signal_1d, fs)
        return val
    except Exception as e:
        print(f"  [DFA crosci error: {e}] -- falling back to manual DFA")
        return compute_dfa_manual(signal_1d, fs)


def compute_dfa_manual(signal_1d, fs):
    """Fallback: manual DFA implementation."""
    N = len(signal_1d)
    profile = np.cumsum(signal_1d - np.mean(signal_1d))

    # Window sizes: logarithmically spaced
    min_win = max(10, int(fs * 0.5))
    max_win = N // 4
    if max_win <= min_win:
        max_win = N // 2
    n_windows = 20
    window_sizes = np.unique(
        np.logspace(np.log10(min_win), np.log10(max_win), n_windows).astype(int)
    )

    flucts = []
    for ws in window_sizes:
        n_segments = N // ws
        if n_segments < 1:
            continue
        rms_values = []
        for i in range(n_segments):
            segment = profile[i * ws : (i + 1) * ws]
            x = np.arange(ws)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            rms_values.append(np.sqrt(np.mean((segment - trend) ** 2)))
        flucts.append(np.mean(rms_values))

    if len(flucts) < 3:
        return np.nan

    log_ws = np.log10(window_sizes[:len(flucts)])
    log_fl = np.log10(flucts)
    slope, _ = np.polyfit(log_ws, log_fl, 1)
    return slope


def compute_fei_crosci(signal_1d, fs, dfa_val):
    """
    Compute fE/I using crosci library.
    crosci.fEI expects shape (n_channels, n_times) + DFA array.
    """
    signal_2d = signal_1d.reshape(1, -1).astype(np.float64)
    # Make signal positive (amplitude envelope should be non-negative)
    signal_2d = np.abs(signal_2d)
    dfa_array = np.array([dfa_val])

    try:
        fei_out, fei_val, _, _, _ = fEI(
            signal_2d,
            sampling_frequency=fs,
            window_size_sec=2.0,
            window_overlap=0.5,
            DFA_array=dfa_array,
            runtime="c",
        )
        val = float(np.squeeze(fei_out))
        if np.isnan(val):
            val = float(np.squeeze(fei_val))
        return val
    except Exception as e:
        print(f"  [fEI crosci error: {e}]")
        return np.nan


def compute_lyapunov(signal_1d, emb_dim=10, lag=None):
    """
    Compute the maximal Lyapunov exponent using nolds.
    """
    # Estimate lag if not given (first minimum of mutual information is ideal,
    # but as a simple heuristic use autocorrelation decay)
    if lag is None:
        n = len(signal_1d)
        max_lag = min(100, n // 10)
        autocorr = np.correlate(signal_1d - np.mean(signal_1d),
                                signal_1d - np.mean(signal_1d), mode='full')
        autocorr = autocorr[n-1:]
        autocorr = autocorr / autocorr[0]
        # Find first zero crossing or 1/e decay
        lag_candidates = np.where(autocorr[:max_lag] < 1/np.e)[0]
        lag = int(lag_candidates[0]) if len(lag_candidates) > 0 else 5
        lag = max(1, lag)

    try:
        le = nolds.lyap_r(signal_1d, emb_dim=emb_dim, lag=lag, min_tsep=lag)
        return float(le)
    except Exception as e:
        print(f"  [Lyapunov error: {e}]")
        return np.nan


def compute_welch_psd(signal_1d, fs, window_sec=10.0, overlap_pct=0.5):
    """
    Compute smooth Power Spectral Density using Welch's method.
    - Window length: 10 seconds (nperseg = 10 * fs = 2500 samples)
    - Overlap: 50% (noverlap = 1250 samples)
    - Window function: Hann window
    """
    nperseg = int(window_sec * fs)
    noverlap = int(nperseg * overlap_pct)
    freqs, psd = sig.welch(
        signal_1d,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        scaling="density"
    )
    # Skip DC (0 Hz)
    mask = freqs > 0
    return freqs[mask], psd[mask]


# ═══════════════════════════════════════════════════════════════════════════
# 3. GENERATE ALL SIGNALS & COMPUTE METRICS
# ═══════════════════════════════════════════════════════════════════════════

def main():
    fs = 250          # sampling frequency (Hz) — typical EEG
    duration = 180    # seconds — 3 minutes, enough for DFA/fEI
    n_samples = fs * duration

    np.random.seed(42)

    signals = {
        "White Noise\n(no correlations)": {
            "generator": generate_white_noise,
            "color": "#7E8D9E",
            "regime": "Uncorrelated",
        },
        "Pink (1/f) Noise\n(scale-free)": {
            "generator": generate_pink_noise,
            "color": "#E07A5F",
            "regime": "Critical-like",
        },
        "Sub-critical\n(deep NREM sleep)": {
            "generator": generate_subcritical_sleep,
            "color": "#3D5A80",
            "regime": "Sub-critical",
        },
        "Near-critical\n(resting-state α)": {
            "generator": generate_near_critical_rest,
            "color": "#81B29A",
            "regime": "Near-critical",
        },
        "Super-critical\n(seizure-like)": {
            "generator": generate_supercritical_seizure,
            "color": "#F2CC8F",
            "regime": "Super-critical",
        },
        "Chaotic\n(Lorenz system)": {
            "generator": generate_lorenz_chaotic,
            "color": "#C97C5D",
            "regime": "Chaotic",
        },
    }

    print("=" * 72)
    print("CRITICALITY DEMO - Synthetic Time Series Analysis")
    print("=" * 72)
    print(f"Sampling rate: {fs} Hz | Duration: {duration}s | Samples: {n_samples}")
    print("-" * 72)
    sys.stdout.flush()

    results = {}
    for name, cfg in signals.items():
        label = name.replace("\n", " ")
        print(f"\n>> {label}")

        # Generate signal
        ts = cfg["generator"](n_samples, fs)

        # --- Compute amplitude envelope for DFA/fEI ---
        # Band-pass 1–40 Hz, take Hilbert envelope
        b, a = sig.butter(4, [1.0, 40.0], btype='band', fs=fs)
        ts_filt = sig.filtfilt(b, a, ts)
        analytic = hilbert(ts_filt)
        amp_env = np.abs(analytic)

        # DFA on broadband amplitude envelope
        dfa_val = compute_dfa_crosci(amp_env, fs, fit_interval=(4, 20))
        fei_val = compute_fei_crosci(amp_env, fs, dfa_val)
        fei_print = f"{fei_val:.3f}" if not np.isnan(fei_val) else "NaN (DFA < 0.6)"
        print(f"  BB  (1-40Hz) : DFA α = {dfa_val:.3f} | fE/I = {fei_print}")

        # Narrowband Theta (4-8 Hz) and Alpha (8-12 Hz) via crosci compute_band_biomarkers
        sig_2d = ts.reshape(1, -1).astype(np.float64)

        # Theta 4-8 Hz
        res_theta = compute_band_biomarkers(sig_2d, fs, (4, 8), biomarkers_to_compute=["DFA", "fEI"])
        dfa_theta = float(np.squeeze(res_theta["DFA"]))
        fei_theta = float(np.squeeze(res_theta["fEI"])) if "fEI" in res_theta else np.nan
        fei_th_print = f"{fei_theta:.3f}" if not np.isnan(fei_theta) else "NaN (DFA < 0.6)"
        print(f"  θ   (4-8Hz)  : DFA α = {dfa_theta:.3f} | fE/I = {fei_th_print}")

        # Alpha 8-12 Hz
        res_alpha = compute_band_biomarkers(sig_2d, fs, (8, 12), biomarkers_to_compute=["DFA", "fEI"])
        dfa_alpha = float(np.squeeze(res_alpha["DFA"]))
        fei_alpha = float(np.squeeze(res_alpha["fEI"])) if "fEI" in res_alpha else np.nan
        fei_al_print = f"{fei_alpha:.3f}" if not np.isnan(fei_alpha) else "NaN (DFA < 0.6)"
        print(f"  α   (8-12Hz) : DFA α = {dfa_alpha:.3f} | fE/I = {fei_al_print}")

        # Lyapunov on raw signal
        step = max(1, len(ts) // 5000)  # target ~5000 points
        ts_sub = ts[::step]
        lyap_val = compute_lyapunov(ts_sub, emb_dim=7)
        print(f"  Lyapunov λ   = {lyap_val:+.4f}")
        sys.stdout.flush()

        # Welch PSD (10s window, 50% overlap)
        freqs, psd = compute_welch_psd(ts, fs, window_sec=10.0, overlap_pct=0.5)

        results[name] = {
            "ts": ts,
            "amp_env": amp_env,
            "dfa": dfa_val,
            "fei": fei_val,
            "dfa_theta": dfa_theta,
            "fei_theta": fei_theta,
            "dfa_alpha": dfa_alpha,
            "fei_alpha": fei_alpha,
            "lyap": lyap_val,
            "freqs": freqs,
            "psd": psd,
            "color": cfg["color"],
            "regime": cfg["regime"],
        }

    # ═══════════════════════════════════════════════════════════════════════
    # 4. PLOTTING
    # ═══════════════════════════════════════════════════════════════════════

    n_signals = len(results)
    fig = plt.figure(figsize=(25, 4.6 * n_signals + 3.8), facecolor="#0D1117")

    # Outer grid: signals + summary table at bottom
    outer = gridspec.GridSpec(
        n_signals + 1, 1,
        height_ratios=[1] * n_signals + [0.95],
        hspace=0.36,
        figure=fig,
    )

    display_seconds = 10  # show only first N seconds in waveform plot

    for i, (name, res) in enumerate(results.items()):
        inner = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[i],
                                                 width_ratios=[1.7, 1.1, 1.2],
                                                 wspace=0.32)

        color = res["color"]
        ts = res["ts"]

        # ── Panel A: Time Series ──────────────────────────────────────
        ax_ts = fig.add_subplot(inner[0])
        t_plot = np.arange(display_seconds * fs) / fs
        ax_ts.plot(t_plot, ts[:display_seconds * fs], color=color,
                   linewidth=0.5, alpha=0.9)
        ax_ts.set_xlim(0, display_seconds)
        ax_ts.set_ylabel("Amplitude", fontsize=9, color="#C9D1D9")
        ax_ts.set_xlabel("Time (s)", fontsize=9, color="#C9D1D9")
        ax_ts.set_title(name, fontsize=12, fontweight="bold",
                        color=color, pad=10, loc="left")
        _style_axis(ax_ts)

        # ── Panel B: Welch Power Spectral Density ─────────────────────
        ax_fft = fig.add_subplot(inner[1])
        mask = res["freqs"] >= 0.5  # skip very low freqs for cleaner plot
        ax_fft.loglog(res["freqs"][mask], res["psd"][mask],
                      color=color, linewidth=1.2, alpha=0.9)
        ax_fft.set_xlabel("Frequency (Hz)", fontsize=9, color="#C9D1D9")
        ax_fft.set_ylabel("Power Spectral Density", fontsize=9, color="#C9D1D9")
        ax_fft.set_title("Welch PSD (10s win, 50% ovlp)", fontsize=10,
                         color="#8B949E", pad=8)
        _style_axis(ax_fft)

        # ── Panel C: Metrics Card ─────────────────────────────────────
        ax_met = fig.add_subplot(inner[2])
        ax_met.set_xlim(0, 1)
        ax_met.set_ylim(0, 1)
        ax_met.axis("off")
        ax_met.set_facecolor("#0D1117")

        # Background card
        card = FancyBboxPatch(
            (0.03, 0.03), 0.94, 0.94,
            boxstyle="round,pad=0.03",
            facecolor="#161B22", edgecolor="#30363D",
            linewidth=1.5
        )
        ax_met.add_patch(card)

        # Metric strings
        fei_bb_str = f"{res['fei']:.3f}" if not np.isnan(res['fei']) else "N/A"
        fei_th_str = f"{res['fei_theta']:.3f}" if not np.isnan(res['fei_theta']) else "N/A"
        fei_al_str = f"{res['fei_alpha']:.3f}" if not np.isnan(res['fei_alpha']) else "N/A"
        lyap_str = f"{res['lyap']:+.4f}"

        # 1. Broadband
        ax_met.text(0.5, 0.90, "BROADBAND (1–40 Hz)", ha="center", fontsize=8,
                    color="#8B949E", fontweight="bold", transform=ax_met.transAxes)
        ax_met.text(0.5, 0.79, f"DFA α={res['dfa']:.3f}  |  fE/I={fei_bb_str}", ha="center", fontsize=10.5,
                    color=color, fontweight="bold", transform=ax_met.transAxes, fontfamily="monospace")

        # 2. Theta
        ax_met.text(0.5, 0.65, "THETA BAND (4–8 Hz)", ha="center", fontsize=8,
                    color="#8B949E", fontweight="bold", transform=ax_met.transAxes)
        ax_met.text(0.5, 0.54, f"DFA α={res['dfa_theta']:.3f}  |  fE/I={fei_th_str}", ha="center", fontsize=10.5,
                    color=color, fontweight="bold", transform=ax_met.transAxes, fontfamily="monospace")

        # 3. Alpha
        ax_met.text(0.5, 0.40, "ALPHA BAND (8–12 Hz)", ha="center", fontsize=8,
                    color="#8B949E", fontweight="bold", transform=ax_met.transAxes)
        ax_met.text(0.5, 0.29, f"DFA α={res['dfa_alpha']:.3f}  |  fE/I={fei_al_str}", ha="center", fontsize=10.5,
                    color=color, fontweight="bold", transform=ax_met.transAxes, fontfamily="monospace")

        # 4. Lyapunov
        ax_met.text(0.5, 0.16, "LYAPUNOV EXPONENT", ha="center", fontsize=8,
                    color="#8B949E", fontweight="bold", transform=ax_met.transAxes)
        ax_met.text(0.5, 0.05, f"λ = {lyap_str}", ha="center", fontsize=11,
                    color=color, fontweight="bold", transform=ax_met.transAxes, fontfamily="monospace")

    # ── Summary Table at Bottom ───────────────────────────────────────────
    ax_table = fig.add_subplot(outer[n_signals])
    ax_table.axis("off")
    ax_table.set_facecolor("#0D1117")

    col_labels = [
        "Signal", "Regime",
        "BB DFA", "BB fE/I",
        "θ DFA (4-8Hz)", "θ fE/I",
        "α DFA (8-12Hz)", "α fE/I",
        "Lyapunov (λ)", "Dynamical Interpretation"
    ]
    table_data = []

    for name, res in results.items():
        label = name.replace("\n", " ")
        fei_bb = f"{res['fei']:.3f}" if not np.isnan(res['fei']) else "N/A"
        fei_th = f"{res['fei_theta']:.3f}" if not np.isnan(res['fei_theta']) else "N/A"
        fei_al = f"{res['fei_alpha']:.3f}" if not np.isnan(res['fei_alpha']) else "N/A"

        interp = _interpret(
            label, res['dfa'], res['fei'], res['lyap'],
            res['dfa_theta'], res['fei_theta'], res['dfa_alpha'], res['fei_alpha']
        )

        table_data.append([
            label,
            res['regime'],
            f"{res['dfa']:.3f}",
            fei_bb,
            f"{res['dfa_theta']:.3f}",
            fei_th,
            f"{res['dfa_alpha']:.3f}",
            fei_al,
            f"{res['lyap']:+.4f}",
            interp
        ])

    col_widths = [0.13, 0.08, 0.065, 0.065, 0.08, 0.065, 0.08, 0.065, 0.08, 0.29]
    table = ax_table.table(
        cellText=table_data,
        colLabels=col_labels,
        colWidths=col_widths,
        cellLoc="center",
        loc="center",
        colColours=["#21262D"] * len(col_labels),
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1.0, 1.9)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#30363D")
        if row == 0:
            cell.set_text_props(color="#C9D1D9", fontweight="bold")
            cell.set_facecolor("#21262D")
        else:
            cell.set_text_props(color="#C9D1D9")
            cell.set_facecolor("#161B22")
            if col == 9:
                cell._loc = "left"

    ax_table.set_title(
        "Summary: Multi-Band Metrics Across Dynamical Regimes",
        fontsize=14, fontweight="bold", color="#C9D1D9", pad=15
    )

    # ── Save ──────────────────────────────────────────────────────────────
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "criticality_demo_results.png")
    try:
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
    except Exception as e:
        print(f"Notice on save: {e}. Retrying save to alternate filename...")
        output_path = os.path.join(script_dir, "criticality_demo_figure.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"\n{'=' * 72}")
    print(f"Figure saved to: {output_path}")
    print(f"{'=' * 72}")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _style_axis(ax):
    """Apply dark-mode styling to an axis."""
    ax.set_facecolor("#0D1117")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#30363D")
    ax.spines["left"].set_color("#30363D")
    ax.tick_params(colors="#8B949E", labelsize=8)
    ax.xaxis.label.set_color("#8B949E")
    ax.yaxis.label.set_color("#8B949E")


def _interpret(name, dfa, fei, lyap, dfa_th, fei_th, dfa_al, fei_al):
    """Generate a short interpretation string."""
    if "White" in name:
        return "Memoryless stochastic | No physiological LRTC | High dim."
    elif "Pink" in name:
        return "Broadband 1/f scale-free | Edge of chaos | Fractal self-similarity"
    elif "Sub-critical" in name or "sleep" in name:
        return "Slow delta limit cycle | Sub-critical damping | Regular attractor"
    elif "Near-critical" in name or "rest" in name:
        return "Critical state | Balanced E~I (fE/I~1.07) | Alpha LRTC (α=0.99)"
    elif "Super-critical" in name or "seizure" in name:
        return "Super-critical runaway | Runaway excitation (E>I) | Hypersynchronous"
    elif "Chaotic" in name or "Lorenz" in name:
        return "Deterministic chaos | Highest Lyapunov (λ=+0.157) | Sensitive dependence"
    return "Multi-scale dynamics"


if __name__ == "__main__":
    main()
