export interface Article {
  id: string;
  index: number;
  title: string;
  source: string;
  readTime: string;
  url?: string;
  category: string;
  summary?: string; // Pre-existing summary
  generatedSummary?: string; // AI generated summary
  isRead: boolean;
  isRemoved: boolean;
}

export interface CategoryGroup {
  id: string;
  title: string;
  emoji: string;
  articles: Article[];
}

export enum AIState {
  IDLE = 'IDLE',
  LOADING = 'LOADING',
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR'
}