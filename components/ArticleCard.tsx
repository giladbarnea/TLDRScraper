import React, { useState } from 'react';
import { Article, AIState } from '../types';
import { generateArticleSummary } from '../services/gemini';
import { Loader2, X } from 'lucide-react';

interface ArticleCardProps {
  article: Article;
  onRemove: (id: string) => void;
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article, onRemove }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [aiState, setAiState] = useState<AIState>(AIState.IDLE);
  const [summaryText, setSummaryText] = useState<string | undefined>(article.generatedSummary);

  const handleExpand = async (e: React.MouseEvent) => {
    e.stopPropagation();

    if (isExpanded) {
      setIsExpanded(false);
      return;
    }

    setIsExpanded(true);

    if (!summaryText && aiState === AIState.IDLE) {
      setAiState(AIState.LOADING);
      try {
        const text = await generateArticleSummary(article.title, article.source);
        setSummaryText(text);
        setAiState(AIState.SUCCESS);
      } catch (error) {
        setSummaryText("Failed to load summary");
        setAiState(AIState.ERROR);
      }
    }
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove(article.id);
  };

  return (
    <article className="group relative pb-16 border-b border-neutral-100">

      <div className="flex items-start justify-between mb-6">
        <div className="text-xs font-mono uppercase tracking-wider text-neutral-400">
          {article.source}
        </div>
        <button
          onClick={handleRemove}
          className="text-neutral-300 hover:text-black transition-colors opacity-0 group-hover:opacity-100"
          title="Remove"
        >
          <X size={14} />
        </button>
      </div>

      <h3
        className="text-2xl font-light leading-tight text-black mb-6 cursor-pointer hover:text-neutral-600 transition-colors"
        onClick={handleExpand}
      >
        {article.title}
      </h3>

      <button
        onClick={handleExpand}
        className="text-xs font-mono uppercase tracking-wider text-neutral-400 hover:text-black transition-colors underline"
      >
        {isExpanded ? 'Close' : 'Read Summary'}
      </button>

      <div
        className={`
          overflow-hidden transition-all duration-500 ease-in-out
          ${isExpanded ? 'max-h-[600px] opacity-100 mt-8' : 'max-h-0 opacity-0 mt-0'}
        `}
      >
        <div className="pt-8 border-t border-neutral-100">
          {aiState === AIState.LOADING ? (
            <div className="flex items-center gap-3 text-neutral-400">
              <Loader2 size={14} className="animate-spin" />
              <span className="text-xs font-mono">Loading</span>
            </div>
          ) : aiState === AIState.ERROR ? (
            <div className="text-xs font-mono text-neutral-400">
              {summaryText}
            </div>
          ) : (
            <div className="animate-fade-in space-y-4 text-base font-light leading-relaxed text-neutral-700">
              {(summaryText || '').split('\n').map((line, i) => (
                <p key={i}>{line.replace(/^[-•*]\s*/, '')}</p>
              ))}
            </div>
          )}
        </div>
      </div>

    </article>
  );
};