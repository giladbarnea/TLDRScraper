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
        setSummaryText("unable to load");
        setAiState(AIState.ERROR);
      }
    }
  };

  return (
    <article className="group bg-warm-paper rounded-3xl p-10 transition-all duration-500">
      <div className="flex items-start justify-between mb-8">
        <div className="text-xs text-warm-accent font-light tracking-wide">{article.source}</div>
        <button onClick={() => onRemove(article.id)} 
                className="text-warm-line hover:text-warm-accent transition-colors opacity-0 group-hover:opacity-100">
          <X size={18} strokeWidth={1} />
        </button>
      </div>
      <h3 className="text-2xl font-serif font-light leading-relaxed text-warm-text mb-8 cursor-pointer hover:text-warm-accent transition-colors" 
          onClick={handleExpand}>
        {article.title}
      </h3>
      <button onClick={handleExpand} 
              className="text-xs text-warm-accent hover:text-warm-text transition-colors underline decoration-warm-line font-light">
        {isExpanded ? 'close' : 'read summary'}
      </button>
      {isExpanded && (
        <div className="mt-10 pt-8 border-t border-warm-line">
          {aiState === AIState.LOADING ? (
            <div className="flex items-center gap-4 text-warm-accent">
              <Loader2 size={16} className="animate-spin" strokeWidth={1} />
              <span className="text-sm font-light">loading</span>
            </div>
          ) : (
            <div className="space-y-5 text-base font-light leading-loose text-warm-text">
              {(summaryText || '').split('\n').map((line, i) => (
                <p key={i}>{line.replace(/^[-•*]\s*/, '')}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
};
