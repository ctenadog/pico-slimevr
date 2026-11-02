"""Optional Tkinter GUI. Imports cleanly on machines without Tk."""

from __future__ import annotations

from . import doctor


def available() -> bool:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


def run_gui() -> int:
    if not available():
        print("Tkinter недоступен. Используйте режим командной строки: pico-slimevr --fix")
        return 1

    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("PICO Motion Tracker -> SlimeVR")
    root.geometry("760x520")

    header = ttk.Label(
        root,
        text="PICO Motion Trackers через SlimeVR Server",
        font=("Segoe UI", 13, "bold"),
    )
    header.pack(anchor="w", padx=12, pady=(12, 4))

    hint = ttk.Label(
        root,
        text="Сначала SteamVR, затем SlimeVR Server. Трекеры PICO отдаются как Vive-трекеры, "
        "feeder SlimeVR забирает их и эмулирует Slime-трекеры.",
        wraplength=720,
        justify="left",
    )
    hint.pack(anchor="w", padx=12)

    tree = ttk.Treeview(root, columns=("status", "detail"), show="tree headings")
    tree.heading("#0", text="Проверка")
    tree.heading("status", text="Статус")
    tree.heading("detail", text="Детали")
    tree.column("#0", width=280)
    tree.column("status", width=90)
    tree.column("detail", width=360)
    tree.pack(fill="both", expand=True, padx=12, pady=10)

    log = tk.Text(root, height=6, wrap="word")
    log.pack(fill="x", padx=12)

    def refresh() -> None:
        tree.delete(*tree.get_children())
        report = doctor.scan()
        for check in report.checks:
            tree.insert(
                "",
                "end",
                text=check.name,
                values=("OK" if check.ok else "ПРОБЛЕМА", check.detail),
            )
        log.delete("1.0", "end")
        log.insert("end", "Готово." if report.ok else "Есть проблемы. Нажмите «Исправить».")

    def apply_fixes() -> None:
        report = doctor.run(fix=True)
        for action in report.applied:
            tag = "изменено" if action.changed else "пропущено"
            log.insert("end", f"\n{action.title}: {tag} — {action.message}")
        refresh()
        messagebox.showinfo("Готово", "Безопасные исправления применены.")

    def apply_roles() -> None:
        report = doctor.apply_roles()
        for action in report.applied:
            tag = "изменено" if action.changed else "пропущено"
            log.insert("end", f"\n{action.title}: {tag} — {action.message}")
        refresh()

    def save_osc() -> None:
        from tkinter import filedialog

        from . import osc

        target = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="vrchat_osc.json",
            filetypes=[("JSON", "*.json")],
        )
        if not target:
            return
        path = doctor.write_osc_profile(Path(target))
        for check in osc.check_ports():
            state = "свободен" if check.free else "занят"
            log.insert("end", f"\nUDP {check.port}: {state}")
        log.insert("end", f"\nШаблон OSC: {path}")

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", padx=12, pady=(0, 12))
    ttk.Button(buttons, text="Проверить", command=refresh).pack(side="left")
    ttk.Button(buttons, text="Исправить", command=apply_fixes).pack(side="left", padx=8)
    ttk.Button(buttons, text="Роли трекеров", command=apply_roles).pack(side="left")
    ttk.Button(buttons, text="Шаблон OSC", command=save_osc).pack(side="left", padx=8)
    ttk.Button(buttons, text="Выход", command=root.destroy).pack(side="right")

    refresh()
    root.mainloop()
    return 0
