# Battery Alert Pro — Landing Site

Static landing page for **Battery Alert Pro**, a Windows battery management utility.

Hosted via **GitHub Pages**.

## Repository layout

The site is served from the **repository root**, so `index.html` lives at the top level
(GitHub Pages does not provide a directory index, so the page itself includes a full
file listing under the *Download* section).

```
.
├── index.html                     # Landing page (entry point)
├── buy_now.html                   # Purchase instructions
├── BatteryAlertPro_Setup.zip      # Installer (recommended download)
├── BatteryAlertProSetup.exe       # Installer (direct download)
├── user_manual.pdf                # 4-page user manual
├── image.png                      # Application icon / favicon
├── main_screen.png                # Screenshot — main settings
├── low_alert.png                  # Screenshot — low battery alert
├── high_alert.png                 # Screenshot — high battery alert
├── sys_tray.png                   # Screenshot — system tray
├── .nojekyll                      # Serve files as-is, skip Jekyll processing
└── README.md
```

## Enabling GitHub Pages

1. Push this folder to a GitHub repository.
2. **Settings → Pages → Build and deployment → Source**: choose **Deploy from a branch**.
3. Select the branch (usually `main`) and folder **`/ (root)`**.
4. The site goes live at `https://<username>.github.io/<repo-name>/`.

### Publishing from a `docs/` folder instead

If you prefer to keep the site in a subfolder, move the contents of this folder into
`docs/` and set **Pages → Source** to the **`/docs`** folder. The relative links inside
the HTML keep working either way.

## Notes

- `index.html` is UTF-8 encoded. The original file was latin-1 with a stray `0xA6`
  byte in the CSS list bullet; this has been corrected to a real `•` (U+2022).
- `BatteryAlertProSetup.exe` is a Windows PE binary. Some browsers and antivirus
  products flag raw `.exe` downloads, which is why the `.zip` is the primary button.
- All paths are relative, so the site works at a repository root, a `docs/` folder, or
  a custom domain without edits.
- The page loads Google Fonts and a `livetrafficfeed.com` visitor-counter widget from
  third-party CDNs. Remove the `<script>` in `index.html` if you would rather not
  include the counter.

## Local preview

```bash
python3 -m http.server 8080
# then open http://localhost:8080/
```
