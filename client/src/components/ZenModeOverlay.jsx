import BaseOverlay, { overlayProseClassName } from './BaseOverlay'

function ZenModeOverlay({ url, html, hostname, displayDomain, articleMeta, onClose, onMarkRemoved }) {
  const truncatedMeta = articleMeta && articleMeta.length > 22
    ? `${articleMeta.slice(0, 22)}...`
    : articleMeta

  return (
    <BaseOverlay
      headerContent={(
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 hover:opacity-70 transition-opacity"
        >
          {hostname && (
            <img
              src={`https://www.google.com/s2/favicons?domain=${hostname}&sz=64`}
              className="w-4 h-4 rounded-full border border-slate-200"
              alt=""
            />
          )}
          <span className="text-sm text-slate-500 font-medium">
            {displayDomain}
            {truncatedMeta && <span className="text-slate-400"> · {truncatedMeta}</span>}
          </span>
        </a>
      )}
      onClose={onClose}
      onMarkRemoved={onMarkRemoved}
    >
      <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
    </BaseOverlay>
  )
}

export default ZenModeOverlay
