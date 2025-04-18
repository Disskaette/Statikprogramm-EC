# Vollwertige Mechanikberechnung für Mehrfeldträger mit Momentenumlagerung (FEM-Balkenmodell) mit externer Eingabeanbindung
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field


@dataclass
class Tragerfeld:
    laenge: float
    streckenlast: float = 0.0  # gleichmäßige Streckenlast [N/m]


@dataclass
class Balkensystem:
    felder: list[Tragerfeld]
    E: float = 210e9  # Elastizitätsmodul [N/m^2]
    I: float = 8.33e-6  # Flächenträgheitsmoment [m^4]

    def berechne_system(self):
        n_felder = len(self.felder)
        n_knoten = n_felder + 1

        dof = 2 * n_knoten
        K = np.zeros((dof, dof))
        f = np.zeros(dof)

        for i, feld in enumerate(self.felder):
            L = feld.laenge
            q = feld.streckenlast

            k_local = (self.E * self.I / L**3) * np.array([
                [12, 6*L, -12, 6*L],
                [6*L, 4*L**2, -6*L, 2*L**2],
                [-12, -6*L, 12, -6*L],
                [6*L, 2*L**2, -6*L, 4*L**2]
            ])

            f_local = q * L / 12 * np.array([6, L, 6, -L])

            dofs = [2*i, 2*i+1, 2*i+2, 2*i+3]

            for a in range(4):
                f[dofs[a]] += f_local[a]
                for b in range(4):
                    K[dofs[a], dofs[b]] += k_local[a, b]

        fixed_dofs = [0, 1, dof-2]  # w0, phi0, wN
        free_dofs = list(set(range(dof)) - set(fixed_dofs))
        K_reduced = K[np.ix_(free_dofs, free_dofs)]
        f_reduced = f[free_dofs]

        u = np.zeros(dof)
        u[free_dofs] = np.linalg.solve(K_reduced, f_reduced)

        self.u = u
        self.K = K
        self.f = f

    def berechne_verlaeufe(self, N=300):
        xs, Ms, Vs, ws = [], [], [], []
        pos = 0
        for i, feld in enumerate(self.felder):
            L = feld.laenge
            q = feld.streckenlast
            x_local = np.linspace(0, L, N // len(self.felder))

            w1 = self.u[2*i]
            phi1 = self.u[2*i+1]
            w2 = self.u[2*i+2]
            phi2 = self.u[2*i+3]

            EI = self.E * self.I

            M = (
                (12 * (w2 - w1) / L**3 - 6 * (phi1 + phi2) / L**2) * x_local**2 +
                (6 * (w1 - w2) / L**2 + (4 * phi1 + 2 * phi2) / L) * x_local +
                q * (L * x_local / 2 - x_local**2 / 2)
            ) * EI

            V = np.gradient(-M, x_local)
            w = (
                (2 * (w2 - w1) / L**3 - (phi1 + phi2) / L**2) * x_local**3 +
                ((3 * w1 - 3 * w2) / L**2 + (2 * phi1 + phi2) / L) * x_local**2 +
                phi1 * x_local + w1
            )

            xs.extend(pos + x_local)
            Ms.extend(-M)
            Vs.extend(V)
            ws.extend(w)
            pos += L

        self.xs = np.array(xs)
        self.Ms = np.array(Ms)
        self.Vs = np.array(Vs)
        self.ws = np.array(ws)

    def zeichne_verlaeufe(self):
        fig, axs = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

        axs[0].plot(self.xs, self.Ms, color='tab:blue')
        axs[0].fill_between(self.xs, self.Ms, 0, color='tab:blue', alpha=0.2)
        axs[0].set_ylabel("M(x) [Nm]")
        axs[0].set_title("Momentenverlauf")
        axs[0].grid(True)

        axs[1].plot(self.xs, self.Vs, color='tab:red')
        axs[1].fill_between(self.xs, self.Vs, 0, color='tab:red', alpha=0.2)
        axs[1].set_ylabel("V(x) [N]")
        axs[1].set_title("Querkraftverlauf")
        axs[1].grid(True)

        axs[2].plot(self.xs, self.ws, color='tab:green')
        axs[2].fill_between(self.xs, self.ws, 0, color='tab:green', alpha=0.2)
        axs[2].set_ylabel("w(x) [m]")
        axs[2].set_title("Durchbiegung")
        axs[2].grid(True)
        axs[2].set_xlabel("x [m]")

        plt.tight_layout()
        plt.show()

# Hilfsfunktion zur Anbindung an GUI


def berechne_und_zeichne(spannweiten: list[float], lasten: list[float]):
    felder = [Tragerfeld(laenge=L, streckenlast=q * 1e3)  # kN/m → N/m
              for L, q in zip(spannweiten, lasten)]
    system = Balkensystem(felder=felder)
    system.berechne_system()
    system.berechne_verlaeufe()
    system.zeichne_verlaeufe()
