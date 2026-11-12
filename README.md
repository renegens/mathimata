# Μαθήματα (Astro)

Στατικό site από Markdown. Τρεις ενότητες: μαθήματα ενηλίκων, Scratch, micro:bit. Περιγραφή συλλογών και frontmatter: `CONTENT.md`.

## Προσθήκη μαθήματος
Πρόσθεσε ένα αρχείο `.md` στη σωστή συλλογή του `src/content/` (π.χ. `adults/25-θέμα.md`) με το frontmatter των υπόλοιπων αρχείων. Αν το frontmatter είναι λάθος, το build αποτυγχάνει. Τα αρχεία λήψης μπαίνουν στο `public/` στο ίδιο μονοπάτι με τον σύνδεσμο.

## Εντολές
- `npm ci` – εγκατάσταση (Node 22)
- `npm run dev` – τοπικός server ανάπτυξης
- `npm run build` – build στο `dist/` (βάση `/`)
- `npm run preview` – προεπισκόπηση του `dist/`
- `npm run check` – τύποι, έλεγχοι περιεχομένου, build και με τις δύο βάσεις και `scripts/check_site.py`

Η βάση διαδρομής ορίζεται από τη μεταβλητή `SITE_BASE` (προεπιλογή `/`). Για GitHub Pages: `SITE_BASE=/mathimata/ npm run build`.

## Δημοσίευση
Κάθε push στο `main` τρέχει το `.github/workflows/pages.yml`, χτίζει με `SITE_BASE=/mathimata/` και δημοσιεύει στο GitHub Pages.
