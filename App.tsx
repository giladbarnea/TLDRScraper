import { Circle } from "lucide-react";
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
		<div className="min-h-screen flex justify-center font-sans bg-zen-bg pb-32">
			<div className="w-full max-w-xl relative">
				<header className="pt-20 pb-12 px-8">
					<div className="flex justify-between items-baseline">
						<h1 className="text-3xl font-light tracking-wide text-zen-text">tldr</h1>
						<button
							onClick={() => setData(INITIAL_DATA)}
							className="text-xs text-zen-subtle hover:text-zen-text transition-colors font-light"
						>
							reset
						</button>
					</div>
				</header>

				<main className="px-8">
					{data.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-32 text-center">
							<Circle size={32} className="mb-8 text-zen-line" strokeWidth={1} />
							<p className="text-zen-subtle text-sm font-light">nothing remains</p>
							<button
								onClick={() => setData(INITIAL_DATA)}
								className="mt-12 text-xs text-zen-text underline font-light"
							>
								reset
							</button>
						</div>
					) : (
						<div className="space-y-16">
							{data.map((group) => (
								<section key={group.id} className="animate-fade-in">
									<h2 className="text-xs font-light text-zen-subtle mb-8 pb-3 border-b border-zen-line">
										{group.title}
									</h2>
									<div className="space-y-12">
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
