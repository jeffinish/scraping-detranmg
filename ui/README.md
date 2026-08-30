# UI (Vite + React)

Cliente Material 3 dos lotes no mart. A API Python continua em `python -m detran_ui`.

```bash
pip install -e ".[ui]"
python -m detran_ui

cd ui
npm install
npm run dev
```

Para um único origin em `:8080`:

```bash
cd ui
npm run build
python -m detran_ui
```
