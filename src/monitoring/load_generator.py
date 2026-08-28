"""
Generateur de trafic pour alimenter Prometheus / Grafana.

Envoie periodiquement des requetes /predict a l'API (a travers nginx) afin que
les panneaux du dashboard (requetes/s, taux d'echec, confidence, latence) aient
de la matiere a afficher.

Stdlib uniquement (urllib) : aucune dependance a installer.

Exemples :
    # trafic nominal, 1 requete toutes les 5 s, jusqu'a Ctrl+C
    python src/monitoring/load_generator.py

    # cadence rapide pendant 10 minutes
    python src/monitoring/load_generator.py --interval 2 --duration 600

    # forcer l'alerte Slack "taux d'echec eleve" (> 20 % soutenu)
    python src/monitoring/load_generator.py --interval 2 --error-rate 0.5

Note : seules les erreurs rendues par l'API (ville inconnue -> 400) apparaissent
dans Prometheus. Une cle API invalide est bloquee par nginx en amont (403) et
n'atteint jamais l'API : elle reste invisible dans les metriques.

    # se limiter a quelques villes
    python src/monitoring/load_generator.py --cities Sydney,Canberra,Darwin
"""
import argparse
import json
import os
import os.path as osp
import random
import signal
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime

PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "..", ".."))
STATIONS_FILE = osp.join(PROJECT_ROOT, "src", "utils", "stations_infos.json")

DEFAULT_URL = "http://localhost:8000/predict"
DEFAULT_API_KEY = os.environ.get("API_KEY", "local-test-key-123")

_stop = False


def _handle_sigint(signum, frame):
    global _stop
    _stop = True
    print("\nArret demande, fin du cycle en cours...")


def load_cities(cities_arg):
    if cities_arg:
        return [c.strip() for c in cities_arg.split(",") if c.strip()]
    with open(STATIONS_FILE) as src:
        stations = json.load(src)
    # Certaines stations n'ont pas d'identifiant BOM : l'API renvoie
    # systematiquement 404 pour celles-la. On les exclut du trafic nominal
    # pour que les seules erreurs soient celles pilotees par --error-rate.
    usable = sorted(c for c, v in stations.items() if v.get("bom_id"))
    skipped = sorted(set(stations) - set(usable))
    if skipped:
        print(f"Villes ignorees (bom_id absent, 404 garanti) : {', '.join(skipped)}")
    return usable


def send_request(url, api_key, city, timeout):
    """Envoie une requete et renvoie (status, latence, payload|None)."""
    body = json.dumps({"city": city}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, time.perf_counter() - start, payload
    except urllib.error.HTTPError as exc:
        return exc.code, time.perf_counter() - start, None
    except Exception as exc:  # connexion refusee, timeout...
        print(f"  !! {type(exc).__name__}: {exc}")
        return 0, time.perf_counter() - start, None


def main():
    parser = argparse.ArgumentParser(
        description="Genere du trafic sur l'API pour alimenter Prometheus/Grafana."
    )
    parser.add_argument("--url", default=DEFAULT_URL, help=f"URL de prediction (defaut: {DEFAULT_URL})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Cle API (defaut: $API_KEY)")
    parser.add_argument("--interval", type=float, default=5.0, help="Secondes entre 2 requetes (defaut: 5)")
    parser.add_argument("--jitter", type=float, default=0.3, help="Variation aleatoire de l'intervalle, 0-1 (defaut: 0.3)")
    parser.add_argument("--error-rate", type=float, default=0.05,
                        help="Proportion de requetes volontairement invalides, 0-1 (defaut: 0.05). "
                             "Au-dela de 0.2 soutenu, l'alerte Slack 'taux d'echec' se declenche.")
    parser.add_argument("--error-kind", choices=("city", "key", "mix"), default="city",
                        help="Type d'erreur simulee (defaut: city). 'city' = ville inconnue -> 400 rendu par "
                             "l'API, visible dans Prometheus. 'key' = cle invalide -> 403 rendu par nginx, "
                             "invisible cote API. 'mix' = les deux.")
    parser.add_argument("--duration", type=float, default=0, help="Duree en secondes (0 = illimite)")
    parser.add_argument("--cities", default=None, help="Liste de villes separees par des virgules")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout par requete (defaut: 30 s)")
    args = parser.parse_args()

    cities = load_cities(args.cities)
    signal.signal(signal.SIGINT, _handle_sigint)

    print(f"Cible        : {args.url}")
    print(f"Villes       : {len(cities)}")
    print(f"Intervalle   : {args.interval}s (jitter {args.jitter:.0%})")
    print(f"Taux d'erreur: {args.error_rate:.0%}")
    print(f"Duree        : {'illimitee' if args.duration <= 0 else str(args.duration) + 's'}  (Ctrl+C pour arreter)\n")

    statuses = Counter()
    confidences = []
    started = time.time()
    n = 0

    while not _stop:
        if args.duration > 0 and (time.time() - started) >= args.duration:
            break

        # Requete volontairement invalide de temps en temps, pour alimenter
        # les metriques d'erreur (4xx/5xx) du dashboard.
        if random.random() < args.error_rate:
            kind_choice = args.error_kind
            if kind_choice == "mix":
                kind_choice = random.choice(("city", "key"))
            if kind_choice == "key":
                # 403 rendu par nginx : la requete n'atteint jamais l'API,
                # donc elle n'apparait PAS dans les metriques Prometheus.
                city, key, kind = random.choice(cities), "cle-invalide", "cle KO"
            else:
                # 400 rendu par l'API : compte bien dans http_requests_total{status="4xx"}.
                city, key, kind = "VilleInexistante", args.api_key, "ville KO"
        else:
            city, key, kind = random.choice(cities), args.api_key, "ok"

        status, latency, payload = send_request(args.url, key, city, args.timeout)
        statuses[status] += 1
        n += 1

        detail = ""
        if payload and isinstance(payload.get("result"), dict):
            conf = payload["result"].get("confidence")
            if conf is not None:
                confidences.append(conf)
                detail = f" | {payload['result'].get('prediction', '')} (conf {conf:.3f})"

        print(f"[{datetime.now():%H:%M:%S}] #{n:<4} {status}  {latency:5.2f}s  {city:<18} [{kind}]{detail}")

        delay = args.interval * (1 + random.uniform(-args.jitter, args.jitter))
        end = time.time() + max(delay, 0.1)
        while time.time() < end and not _stop:
            time.sleep(0.1)

    elapsed = time.time() - started
    ok = sum(c for s, c in statuses.items() if 200 <= s < 300)
    print("\n--- Resume ---")
    print(f"Requetes    : {n} en {elapsed:.0f}s ({n / elapsed if elapsed else 0:.2f}/s)")
    print(f"Statuts     : {dict(sorted(statuses.items()))}")
    print(f"Taux d'echec: {(n - ok) / n:.1%}" if n else "Taux d'echec: n/a")
    if confidences:
        print(f"Confidence  : moy {sum(confidences) / len(confidences):.3f} "
              f"(min {min(confidences):.3f} / max {max(confidences):.3f})")


if __name__ == "__main__":
    main()
