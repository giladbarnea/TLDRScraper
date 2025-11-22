import { Newspaper, RefreshCw, Zap } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { ArticleCard } from "./components/ArticleCard";
import { INITIAL_DATA } from "./data/mockData";
import type { CategoryGroup } from "./types";

const App: React.FC = () => {
	const [data, setData] = useState<CategoryGroup[]>(INITIAL_DATA);
	const [scrolled, setScrolled] = useState(false);

	useEffect(() => {
		const handleScroll = () => setScrolled(window.scrollY > 10);
		window.addEventListener("scroll", handleScroll);
		return () => window.removeEventListener("scroll", handleScroll);
	}, []);

	// Handle removing an article
	const handleRemove = (articleId: string) => {
		setData(
			(prevData) =>
				prevData
					.map((group) => ({
						...group,
						articles: group.articles.filter((a) => a.id !== articleId),
					}))
					.filter((group) => group.articles.length > 0), // Remove empty groups
		);
	};

	const currentDate = new Date().toLocaleDateString("en-US", {
		weekday: "long",
		month: "long",
		day: "numeric",
	});

	return (
		<div className="min-h-screen flex justify-center font-sans bg-[#f8fafc] pb-32">
			<div className="w-full max-w-lg relative">
				{/* Header */}
				<header
					className={`
            sticky top-0 z-40 px-6 py-6 transition-all duration-300 ease-out
            ${scrolled ? "bg-white/90 backdrop-blur-md border-b border-slate-100 shadow-sm" : "bg-transparent"}
          `}
				>
					<div className="flex justify-between items-center">
						<div>
							<h1 className="font-display text-3xl font-extrabold tracking-tight text-slate-900">
								TLDR<span className="text-brand-500">.</span>
							</h1>
							<p
								className={`text-sm font-medium text-slate-500 transition-all duration-300 ${scrolled ? "h-0 opacity-0 overflow-hidden" : "h-auto opacity-100 mt-1"}`}
							>
								{currentDate}
							</p>
						</div>

						<button
							className="group flex items-center justify-center w-10 h-10 rounded-full hover:bg-white hover:shadow-md transition-all duration-300"
							onClick={() => setData(INITIAL_DATA)}
							title="Reset Feed"
						>
							<RefreshCw className="text-slate-400 group-hover:text-brand-600 transition-colors" size={18} />
						</button>
					</div>
				</header>

				{/* Minimalist Ticker */}
				<div
					className={`
            px-6 mb-8 transition-all duration-500 ease-in-out
            ${scrolled ? "opacity-0 h-0 -mt-4 overflow-hidden" : "opacity-100 h-auto"}
        `}
				>
					<div className="bg-white rounded-2xl p-4 shadow-soft border border-slate-50 flex items-start gap-3">
						<div className="mt-1 bg-brand-50 p-1.5 rounded-lg">
							<Zap className="text-brand-600" size={16} />
						</div>
						<p className="text-sm text-slate-600 font-medium leading-relaxed">
							<span className="font-bold text-slate-900">Daily Insight:</span> The AI landscape is shifting from
							generative text to physical infrastructure and energy solutions.
						</p>
					</div>
				</div>

				{/* Main Content */}
				<main className="px-6 space-y-10">
					{data.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-32 opacity-0 animate-fade-in text-center">
							<div className="w-20 h-20 bg-white shadow-soft rounded-full flex items-center justify-center mb-6">
								<Newspaper className="w-8 h-8 text-slate-300" />
							</div>
							<h3 className="font-display text-xl font-bold text-slate-900 mb-2">All caught up</h3>
							<p className="text-slate-500 max-w-xs mx-auto leading-relaxed">
								You've cleared your reading list. Enjoy the rest of your day.
							</p>
							<button
								className="mt-8 px-8 py-3 rounded-full bg-slate-900 text-white text-sm font-semibold tracking-wide hover:bg-brand-600 hover:shadow-lg hover:shadow-brand-500/30 transition-all"
								onClick={() => setData(INITIAL_DATA)}
							>
								Reset Feed
							</button>
						</div>
					) : (
						data.map((group) => (
							<section className="space-y-5 animate-slide-up" key={group.id}>
								<div className="flex items-center gap-3 pl-1">
									<span className="text-xl">{group.emoji}</span>
									<h2 className="font-display font-bold text-lg text-slate-900">{group.title}</h2>
								</div>

								<div className="space-y-4">
									{group.articles.map((article) => (
										<ArticleCard article={article} key={article.id} onRemove={handleRemove} />
									))}
								</div>
							</section>
						))
					)}
				</main>
			</div>
		</div>
	);
};

export default App;
