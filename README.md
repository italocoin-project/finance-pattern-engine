# Finance Pattern Engine

Monitor informativo dei mercati crypto con interfaccia in italiano, confronto tra exchange, grafici e archivio storico verificabile nel repository.

## Pubblicazione
- Sito: https://italocoin-project.github.io/finance-pattern-engine/
- Repository e archivio dati: https://github.com/italocoin-project/finance-pattern-engine

## Funzioni
- Monitor live con quotazioni spot pubbliche da Binance, Coinbase, OKX e Kraken, quando raggiungibili.
- Monitor di 30 asset e confronto indicativo tra prezzi.
- Classifica con capitalizzazione di mercato, supply circolante, volume 24h e dominanza di Bitcoin tramite CoinGecko, con prezzi Binance quando disponibili.
- Classifica globale consultabile a pagine fino alle prime 250 criptovalute per capitalizzazione (`markets.html`), con ricerca, ordinamento, prezzo, variazioni 24h/7g, volume e supply.
- Schede crypto (`coin.html?id=...`) con metriche fondamentali, descrizione, link ufficiali e grafici interattivi su 1 giorno, 7 giorni, 1 mese, 1 anno e storico completo.
- Grafico a candele orarie selezionabili da 1 a 24 ore, con fallback Binance → OKX → Kraken.
- Archivio di campioni orari in `data/market/YYYY-MM-DD.jsonl`, raccolti tramite GitHub Actions.
- Filtri storico da 1 a 24 ore, 7 giorni, 30 giorni, 90 giorni, un anno e archivio disponibile.
- Analisi di file di movimenti importati localmente nel browser; budget e snapshot personali restano locali.
- Guide educative e pagine informative.

## Fonti dei dati di mercato
Le quotazioni exchange provengono dagli endpoint pubblici di Binance; capitalizzazione, supply, dominanza di Bitcoin, descrizioni e grafici delle schede provengono dall’API pubblica CoinGecko. Le API possono applicare limiti di frequenza o non essere disponibili: il sito segnala i dati mancanti invece di inventarli. I valori possono essere aggiornati con ritardo e non sono una garanzia per decisioni finanziarie.

## Raccolta dati
Il workflow `.github/workflows/archive-market-data.yml` è pianificato ogni ora. Il programma `scripts/archive_market_data.py` interroga endpoint pubblici per 30 asset e quattro exchange, salva il timestamp UTC e registra gli errori per le fonti non raggiungibili. Non inventa quotazioni mancanti. Alcuni endpoint possono restituire errori HTTP in base alla regione, alle restrizioni dell'exchange o alle regole anti-bot.

L'archivio inizia dalla prima raccolta riuscita: non è possibile ricostruire retroattivamente campioni non registrati. I campioni orari non equivalgono a tick-by-tick e non sono transazioni blockchain.

## Limiti e sicurezza
- Le API pubbliche dei prezzi non forniscono movimenti privati degli account Binance/Coinbase.
- Non caricare password, seed phrase, chiavi API private o dati sensibili.
- I link ai block explorer possono verificare una transazione soltanto quando esiste un hash on-chain valido per la rete corretta.
- Le differenze tra prezzi USD e USDT, le commissioni, lo slippage e la liquidità impediscono di interpretare lo spread come profitto garantito.
- Gli indicatori sono descrittivi e non sono consulenza finanziaria.

## Verifiche automatiche
- La workflow `Validate site and data collector` controlla la sintassi JavaScript, la compilazione Python, lo schema della sitemap e la coerenza dell'elenco dei 30 asset.
- `scripts/test_archive_market_data.py` esegue test offline con risposte API simulate: non effettua ordini, non richiede chiavi API e non usa prezzi fittizi nel sito.
- Gli endpoint pubblici possono essere bloccati o limitati in base alla regione; in questi casi il dato viene segnalato come non disponibile e non sostituito con una quotazione inventata.

## Pubblicità
Prima di attivare Google AdSense, il gestore deve completare l'informativa privacy, inserire i dati reali del titolare e implementare i consensi/cookie richiesti per i visitatori interessati. Non sono stati inventati ID publisher o contatti.
