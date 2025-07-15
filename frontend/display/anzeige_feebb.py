

def update_maxwerte(self):
    self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_moment_kalt.config(
        text=f"{result['GZT']['max']['moment']:.1f}"))
    self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_querkraft_kalt.config(
        text=f"{result['GZT']['max']['querkraft']:.1f}"))


def zeichne_gzt_verlaeufe(self):
    import matplotlib.pyplot as plt  # <- Lokaler Import
    if self.eingabemaske.schnittgroeßen_anzeige_button.get():
        # Schnittkräfte definieren
        result
        moment = self.system_memory['GZT']['moment']
        querkraft = self.system_memory['GZT']['querkraft']
        durchbiegung = self.system_memory['GZT']['durchbiegung']
        x = np.linspace(0, 1, len(moment))

        fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

        axs[0].plot(x, np.array(moment) / 1e6, color='tab:blue')
        axs[0].fill_between(x, np.array(moment) / 1e6,
                            0, color='tab:blue', alpha=0.3)
        axs[0].set_ylabel("M(x) [kNm]")
        axs[0].set_title("Momentenverlauf (GZT)")
        axs[0].grid(True)

        axs[1].plot(x, np.array(querkraft) / 1e3, color='tab:red')
        axs[1].fill_between(x, np.array(querkraft) / 1e3,
                            0, color='tab:red', alpha=0.3)
        axs[1].set_ylabel("V(x) [kN]")
        axs[1].set_title("Querkraftverlauf (GZT)")
        axs[1].grid(True)

        axs[2].plot(x, durchbiegung, color='tab:green')
        axs[2].fill_between(x, durchbiegung, 0,
                            color='tab:green', alpha=0.3)
        axs[2].set_ylabel("w(x) [mm]")
        axs[2].set_title("Durchbiegung (GZT)")
        axs[2].set_xlabel("normierte Trägerlänge")
        axs[2].grid(True)

        plt.tight_layout()

        # Neuen tkinter-Plot-Dialog öffnen
        fenster = tk.Toplevel(self.eingabemaske.root)
        fenster.title("Schnittkraftverläufe GZT")
        fenster.geometry("1000x800")

        canvas = FigureCanvasTkAgg(fig, master=fenster)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    else:
        plt.close('all')
