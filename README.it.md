# Netgear Orbi: risolvere il "wan lan conflict" (pannello bloccato, satelliti magenta, mesh lenta)

[English](README.md) · **Italiano** · [Español](README.es.md)

Guida pratica per router Netgear Orbi (provata su **RBR760 / RBK760, firmware V6.3.8.13_1.4.84**) collegati dietro un modem del provider che usa la stessa sottorete dell'Orbi. Altri modelli Orbi usano la stessa famiglia di firmware, quindi probabilmente vale anche per loro.

## Sintomi

Probabilmente hai questo problema se ti ritrovi in più punti di questa lista:

- Il pannello Orbi (`orbilogin.com` / `http://10.0.0.1`) mostra una pagina bianca, un 404, oppure una pagina *"Important Update … IP address was updated to 10.0.0.1"* senza un pulsante **CONTINUE** funzionante.
- La LAN dell'Orbi è passata all'improvviso da `192.168.1.x` a `10.0.0.x`.
- Tutte le chiamate API del pannello rispondono `{"code":8,"msg":"wan lan conflict"}` (si vede negli strumenti per sviluppatori del browser, scheda Rete).
- I satelliti hanno il LED **magenta**, oppure il pannello li elenca come semplici dispositivi "Cablato" con *Numero di satelliti: 0*.
- La radio 5 GHz mostra **"Canale 0"**, *5G WLAN: Link down*, e tutti i client stanno sui 2,4 GHz.
- In *Avanzate → MOSTRA STATISTICHE* il backhaul è circa **573 Mbps** (2,4 GHz) invece di **~2400 Mbps** (5 GHz). Le stanze servite da un satellite vanno a ~90 Mbps invece di diverse centinaia.
- Il problema **ritorna a ogni riavvio** dell'Orbi.

## Causa

Il modem del provider e l'Orbi usano entrambi `192.168.1.0/24` (molto comune: il TIM Hub / Technicolor e tanti altri modem usano `192.168.1.1`). La WAN dell'Orbi riceve dal modem un indirizzo `192.168.1.x`, che si sovrappone alla sua LAN.

Il firmware rileva la sovrapposizione ("wan lan conflict") e:

1. sposta d'emergenza la propria LAN su `10.0.0.1`;
2. reindirizza il pannello alla pagina `/conflict`, dove si conferma con **CONTINUE**;
3. blocca le API (`code 8`) finché non confermi.

**Il bug:** il server web del router non serve `/conflict` (HTTP 404), quindi la pagina di conferma non si carica mai e il pannello è inutilizzabile. Siccome la vecchia impostazione LAN resta salvata, il conflitto ritorna a ogni riavvio. In questo stato la mesh funziona degradata (radio 5 GHz giù, satelliti non sincronizzati, backhaul sui 2,4 GHz).

## Soluzione rapida

Servono due cose: (A) superare una volta la pagina `/conflict` rotta, e (B) eliminare la sovrapposizione di sottorete perché non ritorni.

### A. Sbloccare il pannello

Scegli una delle due opzioni:

**Opzione 1, script Playwright (provato).** Serve Node.js.

```bash
cd tools
npm install playwright
npx playwright install chromium
node unlock-conflict.mjs            # oppure: node unlock-conflict.mjs http://<ip-orbi>
```

Si apre una finestra del browser. Fai il login con la password admin dell'Orbi; lo script preme CONTINUE al posto tuo e stampa la risposta del router (deve essere `{"code":0,...}`). Lascia la finestra aperta e passa alla parte B.

**Opzione 2, proxy con cache.** Serve Python 3, nessun pacchetto aggiuntivo.

```bash
python tools/orbi_proxy.py          # ORBI_HOST=<ip-orbi> se non è 10.0.0.1
```

Apri `http://127.0.0.1:8088/index.html`, fai il login e premi CONTINUE. Il proxy risponde a `/conflict` con `index.html`, così la pagina di conferma si carica. Inoltre mette in cache il bundle JavaScript da 5-6 MB e rende il pannello usabile anche con un Wi-Fi debole (vedi [Consigli](#consigli)). La parte di sblocco di questa opzione non è stata provata con il router in stato di conflitto; se non funziona usa l'opzione 1.

Note:

- Usa `http://10.0.0.1` invece di `orbilogin.com`: con il DNS sicuro (DoH) attivo il browser spesso non risolve `orbilogin.com`. Con `https://` compare un errore di certificato.
- Chiamare `/dniapi/conflict` a mano (curl, fetch) non funziona: le API richiedono un token e una firma calcolati dal JavaScript del pannello.

### B. Eliminare la sovrapposizione di sottorete

Fai almeno una di queste cose, in ordine di preferenza:

1. **Cambia la LAN del modem del provider** in un'altra sottorete, ad esempio `192.168.10.1/24` (DHCP `192.168.10.2-254`). Alcuni modem rifiutano certi intervalli: il TIM Hub ad esempio rifiuta `192.168.2.x` con *"Gateway IP should not be in sfp IP Range"*, mentre `192.168.10.x` è accettato. Aggiorna anche eventuali prenotazioni DHCP e regole DMZ / port forwarding che puntano all'Orbi.
2. **Rendi permanente la LAN dell'Orbi:** *Avanzate → Installazione → Impostazione LAN*, tieni o imposta una sottorete diversa da quella del modem (es. `10.0.0.1/24`) e premi **APPLICA**. Il router si riavvia e l'impostazione resta salvata, invece di essere solo il ripiego d'emergenza.
3. In alternativa, se non ti servono le funzioni di routing dell'Orbi, mettilo in **modalità AP** (*Avanzate → Impostazioni avanzate → Modalità router / AP*), così non ha una sottorete LAN propria.

### C. Aggiornare l'indirizzo WAN dell'Orbi

Dopo aver cambiato la sottorete del modem, l'Orbi tiene per ore il vecchio lease WAN (`192.168.1.x`), anche dopo un riavvio, e Internet smette di funzionare. Si risolve con:

*Avanzate → Home → **STATO CONNESSIONE*** (si apre in una nuova scheda) → **Rilascia** → **Rinnova**.

Ora la WAN deve mostrare un indirizzo nella nuova sottorete (es. `192.168.10.x`) con il modem come gateway e DNS.

### D. Riavviare una volta, poi aspettare

Riavvia una volta il router Orbi (*Avanzate → Home → RIAVVIA*, oppure dall'app Orbi). Poi controlla *Avanzate → Home → MOSTRA STATISTICHE* e *Dispositivi collegati*:

- 5G WLAN deve mostrare ~2400M e un canale vero (es. *36+40+…+64, fino a 2401 Mbps*), non *Canale 0*.
- I satelliti devono comparire in **Satelliti connessi**, non come client cablati.
- **Abbi pazienza:** nei primi ~15 minuti dopo il riavvio i satelliti possono restare sul backhaul 2,4 GHz (573M). Nel nostro caso dopo sono passati da soli ai 5 GHz (2401M).

Salvare le impostazioni wireless senza modifiche, o cambiare il canale 5 GHz, **non** ha fatto ripartire la radio 5 GHz; c'è voluto un riavvio dopo aver eliminato il conflitto.

## Risultati (un caso reale)

| | Prima | Dopo |
|---|---|---|
| Pannello Orbi | bloccato su `/conflict` 404 | funziona |
| Radio 5 GHz | Canale 0, link down | 36-64, 2401 Mbps |
| Satelliti | magenta / "cablati", 0 sincronizzati | 2 connessi, backhaul "buona" |
| Backhaul | 573 Mbps (2,4 GHz) | 2401 Mbps (5 GHz) |
| Download in una stanza con satellite (via cavo) | ~90 Mbps | ~200-300 Mbps (server di test esteri) |

## Consigli

- **Satellite ancora magenta?** Non forzare *Aggiungi satellite Orbi* più e più volte: le sincronizzazioni ripetute rimescolano la mesh e peggiorano tutto. Premi prima il tasto **Sync** sul satellite, poi *SINCRONIZZA* nel pannello entro 2 minuti, possibilmente con il satellite vicino al router.
- **Il pannello non finisce mai di caricare via Wi-Fi?** Il bundle JavaScript del pannello pesa 5-6 MB e su collegamenti con perdite non arriva. `tools/orbi_proxy.py` lo mette in cache al primo caricamento, poi il pannello si apre in 1-3 s. Puoi avviare un proxy per ogni dispositivo, es. `ORBI_HOST=10.0.0.11 PROXY_PORT=8089` per un satellite.
- **Canali DFS.** A 160 MHz il fronthaul 5 GHz usa i canali 52-64 (DFS); il rilevamento radar può causare cambi di canale improvvisi e disconnessioni. Se vedi cadute casuali prova 80 MHz su canale fisso (36 o 44).
- **PC Windows bloccato a 11 Mbps sui 2,4 GHz?** Controlla la proprietà avanzata della scheda Wi-Fi *"2.4G Wireless Mode"*: il valore `IEEE 802.11b` forza le velocità legacy. Deve essere `IEEE 802.11b/g/n/ax`.
- **Test di velocità:** usa un server nel tuo paese; i server lontani limitano il risultato ben sotto una linea da 1 gigabit.

## Contenuto del repository

| File | Scopo |
|---|---|
| `tools/unlock-conflict.mjs` | Script Playwright che aggira la pagina `/conflict` rotta e preme CONTINUE |
| `tools/orbi_proxy.py` | Proxy locale con cache per il pannello Orbi (solo libreria standard di Python 3) |

## Avvertenze

Progetto non affiliato a Netgear. Modificare le impostazioni del router può interrompere la connessione; prima di cambiare la LAN del modem assicurati di poterlo raggiungere via cavo e annota i valori precedenti. Usa a tuo rischio.

## Licenza

[MIT](LICENSE) © lambdagw
