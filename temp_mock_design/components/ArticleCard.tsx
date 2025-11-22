import { Bot, Loader2, Minus, Sparkles, Trash2 } from "lucide-react";
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
		e.stopPropagation(); // Prevent triggering if nested

		if (isExpanded) {
			setIsExpanded(false);
			return;
		}

		setIsExpanded(true);

		// If we don't have a summary yet, fetch it
		if (!summaryText && aiState === AIState.IDLE) {
			setAiState(AIState.LOADING);
			try {
				const text = await generateArticleSummary(article.title, article.source);
				setSummaryText(text);
				setAiState(AIState.SUCCESS);
			} catch (error) {
				setSummaryText("Failed to load summary. Please check your connection.");
				setAiState(AIState.ERROR);
			}
		}
	};

	const handleRemove = (e: React.MouseEvent) => {
		e.stopPropagation();
		onRemove(article.id);
	};

	return (
		<div
			className={`
        group relative bg-white transition-all duration-300 border border-slate-100
        rounded-2xl shadow-soft hover:shadow-soft-hover
        ${isExpanded ? "mb-6 ring-1 ring-brand-100" : "mb-0"}
      `}
		>
			<div className="p-5 flex flex-col gap-2">
				{/* Header / Meta */}
				<div className="flex items-center justify-between mb-1">
					<div className="flex items-center gap-2">
						<span className="text-[11px] font-bold tracking-wider uppercase text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md">
							{article.source}
						</span>
					</div>
					<span className="text-[11px] font-medium text-slate-400">{article.readTime}</span>
				</div>

				{/* Title */}
				<h3
					className="text-[19px] font-display font-bold leading-snug text-slate-900 group-hover:text-brand-600 transition-colors duration-200 cursor-pointer"
					onClick={handleExpand}
				>
					{article.title}
				</h3>

				{/* Actions Bar */}
				<div className="flex items-center justify-between mt-3 pt-1">
					<button
						className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-200
              ${
								isExpanded
									? "bg-slate-100 text-slate-600 hover:bg-slate-200"
									: "bg-brand-50 text-brand-600 hover:bg-brand-100"
							}
            `}
						onClick={handleExpand}
					>
						{isExpanded ? (
							<span className="flex items-center gap-1.5">
								<Minus size={12} /> Close
							</span>
						) : (
							<span className="flex items-center gap-1.5">
								<Sparkles size={12} /> TLDR
							</span>
						)}
					</button>

					<button
						className="text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-full p-2 transition-all opacity-0 group-hover:opacity-100"
						onClick={handleRemove}
						title="Remove"
					>
						<Trash2 size={14} />
					</button>
				</div>

				{/* AI Content Area */}
				<div
					className={`
            overflow-hidden transition-all duration-500 ease-[cubic-bezier(0.25,0.1,0.25,1.0)]
            ${isExpanded ? "max-h-[500px] opacity-100 mt-4 border-t border-slate-50 pt-4" : "max-h-0 opacity-0 mt-0"}
          `}
				>
					<div className="relative">
						{aiState === AIState.LOADING ? (
							<div className="flex items-center gap-3 text-brand-600 py-2">
								<Loader2 className="animate-spin" size={16} />
								<span className="text-sm font-medium font-display">Analyzing content...</span>
							</div>
						) : aiState === AIState.ERROR ? (
							<div className="text-xs text-red-500 py-2">{summaryText}</div>
						) : (
							<div className="animate-fade-in">
								<div className="flex items-center gap-2 mb-3">
									<Bot className="text-brand-500" size={14} />
									<span className="text-xs font-bold uppercase tracking-wider text-slate-500">Gemini Insight</span>
								</div>
								<div className="space-y-3 text-slate-700 leading-relaxed text-[15px] font-normal font-sans">
									{(summaryText || "").split("\n").map((line, i) => (
										<div className="flex gap-3 items-start" key={i}>
											<span className="text-brand-300 text-[10px] mt-1.5">●</span>
											<span>{line.replace(/^[-•*]\s*/, "")}</span>
										</div>
									))}
								</div>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
};
