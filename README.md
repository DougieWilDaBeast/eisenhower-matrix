# Eisenhower Matrix website

The public site for the Android app [Eisenhower Matrix: To-Do List](https://play.google.com/store/apps/details?id=com.willjkdouglas.eisenhower_matrix).

Served by GitHub Pages from the `main` branch at https://willtoforge.com/eisenhower-matrix/

- `index.html`: the whole site in English (the method, a short guide, the app, questions). It is generated, see below
- `de/`, `es/`, `fr/`, `it/`, `pt/`, `nl/`, `pl/`, `tr/`, `ru/`, `id/`: the same page translated, each with its own printable PDFs
- `_i18n/`: source for all the home pages. `template.html` is the layout, `strings/<lang>.json` the text, `languages.json` the list of languages
- `eisenhower-matrix-template.pdf`, `eisenhower-matrix-template-letter.pdf`: free printable matrix, A4 and US Letter
- `blog/`: blog posts as plain HTML pages sharing `blog/blog.css`; add each new post to `blog/index.html`, `sitemap.xml` and the list on the home page
- `img/`: app icon and screenshots
- `sitemap.xml`: for search engines (home page entries are generated with their language alternates; blog entries are kept)

## Changing the home page

Edit `_i18n/template.html` or `_i18n/strings/en.json` (and the same key in every other language file), then run:

```
python3 _i18n/build.py          # all home pages + sitemap
python3 _i18n/build.py --pdf    # also the translated PDFs (needs node + Playwright)
```

The build stops if a language file is missing a key. To add a language, add it to `languages.json` and copy `en.json` to `strings/<code>.json`. The English PDFs at the root are never regenerated. Every page links to the others with hreflang tags. Blog posts and the privacy policy stay English only.

Contact: eisenhower.mtrx@gmail.com
