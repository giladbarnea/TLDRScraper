/**
 * Per-domain color palettes for article cards and the reading-overlay header.
 *
 * THIS IS THE ONLY PLACE TO ADD A SOURCE. Map a hostname to its four colors and
 * both the card and the overlay header adopt them automatically — the colors are
 * injected as CSS variables (see `style={sourceTheme}` in ArticleCard/BaseOverlay)
 * and consumed by the generic rules in sourceThemes.css.
 *
 * To add a source: copy a block, set the hostname, and pick its four colors —
 * text (primary), dim (secondary), background, and border.
 */
export const SOURCE_THEMES = {
  'github.com': {
    '--card-text': '#e6edf3',
    '--card-dim': '#8b949e',
    '--card-bg': '#0d1117',
    '--card-border': '#30363d',
  },
}

export function getSourceTheme(hostname) {
  return SOURCE_THEMES[hostname]
}
