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
		<div className="min-h-screen flex justify-center font-sans bg-warm-bg pb-40">
			<div className="w-full max-w-2xl relative">
				<header className="pt-24 pb-16 px-12">
					<div className="flex justify-between items-center">
						<h1 className="text-4xl font-serif font-light text-warm-text">tldr</h1>
						<button
							className="text-xs text-warm-accent hover:text-warm-text transition-colors font-light"
							onClick={() => setData(INITIAL_DATA)}
						>
							reset
						</button>
					</div>
				</header>
				<main className="px-12">
					{data.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-40 text-center">
							<Circle className="mb-12 text-warm-line" size={40} strokeWidth={0.5} />
							<p className="text-warm-accent text-sm font-light">nothing here</p>
							<button
								className="mt-16 text-xs text-warm-accent underline font-light"
								onClick={() => setData(INITIAL_DATA)}
							>
								reset
							</button>
						</div>
					) : (
						<div className="space-y-20">
							{data.map((group) => (
								<section key={group.id}>
									<h2 className="text-xs font-light text-warm-accent mb-12 pb-4 border-b border-warm-line tracking-wider">
										{group.title}
									</h2>
									<div className="space-y-16">
										{group.articles.map((article) => (
											<ArticleCard article={article} key={article.id} onRemove={handleRemove} />
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
