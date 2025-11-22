import { Loader2, X } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { generateArticleSummary } from "../services/gemini";
import { AIState, type Article } from "../types";

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

	const handleRemove = (e: React.MouseEvent) => {
		e.stopPropagation();
		onRemove(article.id);
	};

	return (
		<article className="group">
			<div className="flex items-start justify-between mb-5">
				<div className="text-xs text-zen-subtle font-light">{article.source}</div>
				<button
					onClick={handleRemove}
					className="text-zen-line hover:text-zen-text transition-colors opacity-0 group-hover:opacity-100"
				>
					<X size={16} strokeWidth={1.5} />
				</button>
			</div>

			<h3
				className="text-xl font-light leading-relaxed text-zen-text mb-6 cursor-pointer hover:text-zen-subtle transition-colors"
				onClick={handleExpand}
			>
				{article.title}
			</h3>

			<button
				onClick={handleExpand}
				className="text-xs text-zen-subtle hover:text-zen-text transition-colors underline decoration-zen-line font-light"
			>
				{isExpanded ? "close" : "read summary"}
			</button>

			<div
				className={
					isExpanded
						? "mt-8 max-h-[500px] opacity-100 overflow-hidden transition-all duration-700 ease-in-out"
						: "mt-0 max-h-0 opacity-0 overflow-hidden transition-all duration-700 ease-in-out"
				}
			>
				<div className="pt-6 border-t border-zen-line">
					{aiState === AIState.LOADING ? (
						<div className="flex items-center gap-3 text-zen-subtle">
							<Loader2 size={14} className="animate-spin" strokeWidth={1.5} />
							<span className="text-xs font-light">loading</span>
						</div>
					) : aiState === AIState.ERROR ? (
						<div className="text-xs font-light text-zen-subtle">{summaryText}</div>
					) : (
						<div className="animate-fade-in space-y-4 text-sm font-light leading-relaxed text-zen-text">
							{(summaryText || "").split("\n").map((line, i) => (
								<p key={i}>{line.replace(/^[-•*]\s*/, "")}</p>
							))}
						</div>
					)}
				</div>
			</div>
		</article>
	);
};
