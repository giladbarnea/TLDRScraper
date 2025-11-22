import { Minus } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { ArticleCard } from "./components/ArticleCard";
import { INITIAL_DATA } from "./data/mockData";
import type { CategoryGroup } from "./types";

const App: React.FC = () => {
	const [data, setData] = useState<CategoryGroup[]>(INITIAL_DATA);

	const handleRemove = (articleId: string) => {
		setData((prevData) =>
			prevData
				.map((group) => ({
					...group,
					articles: group.articles.filter((a) => a.id !== articleId),
				}))
				.filter((group) => group.articles.length > 0),
		);
	};

	return (
		<div className="min-h-screen flex justify-center font-sans bg-white pb-40">
			<div className="w-full max-w-2xl relative">
				<header className="pt-16 pb-12 px-8 border-b border-neutral-200">
					<div className="flex justify-between items-baseline">
						<h1 className="text-5xl font-light tracking-tight text-black">TLDR</h1>
						<button
							onClick={() => setData(INITIAL_DATA)}
							className="text-xs font-mono uppercase tracking-wider text-neutral-400 hover:text-black transition-colors"
						>
							Reset
						</button>
					</div>
				</header>

				<main className="px-8 pt-16">
					{data.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-40 text-center">
							<Minus size={20} className="mb-8 text-neutral-300" />
							<p className="text-neutral-400 text-sm font-mono">Nothing here</p>
							<button
								onClick={() => setData(INITIAL_DATA)}
								className="mt-12 text-xs font-mono uppercase tracking-wider text-black underline"
							>
								Reset
							</button>
						</div>
					) : (
						<div className="space-y-20">
							{data.map((group) => (
								<section key={group.id} className="animate-fade-in">
									<h2 className="text-xs font-mono uppercase tracking-widest text-neutral-400 mb-12 border-b border-neutral-100 pb-4">
										{group.title}
									</h2>
									<div className="space-y-16">
										{group.articles.map((article) => (
											<ArticleCard key={article.id} article={article} onRemove={handleRemove} />
										))}
									</div>
								</section>
							))}
						</div>
					)}
				</main>
			</div>
		</div>
	);
};

export default App;
