import type { CategoryGroup } from "../types";

export const INITIAL_DATA: CategoryGroup[] = [
	{
		id: "big-tech",
		title: "Big Tech & Startups",
		emoji: "📱",
		articles: [
			{
				id: "a1",
				index: 1,
				title: "Blue Origin No Longer Just a Rocket Company as Mars 'on Radar'",
				source: "Bloomberg",
				readTime: "1 minute read",
				category: "Big Tech & Startups",
				isRead: false,
				isRemoved: false,
			},
			{
				id: "a2",
				index: 2,
				title: "Jeff Bezos Creates AI Start-Up Where He Will Be Co-Chief Executive",
				source: "New York Times",
				readTime: "5 minute read",
				category: "Big Tech & Startups",
				isRead: false,
				isRemoved: false,
			},
			{
				id: "a3",
				index: 12,
				title: "Middlemen Are Eating the World (And That's Good, Actually)",
				source: "Substack",
				readTime: "7 minute read",
				category: "Big Tech & Startups",
				isRead: true, // Example of read state
				isRemoved: false,
			},
		],
	},
	{
		id: "science",
		title: "Science & Futuristic Technology",
		emoji: "🚀",
		articles: [
			{
				id: "b1",
				index: 3,
				title: "China is one step closer to perpetual energy independence with fusion breakthrough",
				source: "Reuters",
				readTime: "9 minute read",
				category: "Science",
				isRead: false,
				isRemoved: false,
			},
			{
				id: "b2",
				index: 4,
				title: "SpaceX Starship successful landing marks new era of space travel",
				source: "TechCrunch",
				readTime: "3 minute read",
				category: "Science",
				isRead: false,
				isRemoved: false,
			},
		],
	},
];
