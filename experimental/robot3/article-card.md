This is a fantastic example because your current component is juggling two separate hooks (useArticleState and useSummary) that actually depend on each other. This is exactly where bugs happen—when useArticleState thinks it's "removed" but useSummary is still "loading."
Here is how we consolidate all that logic into a single Robot3 machine.
1. The Machine Definition (articleMachine.js)
We define one machine that rules them all. No more syncing two hooks.
import { createMachine, state, transition, reduce, invoke, guard, immediate } from 'robot3';

// 1. Context: Holds the data that changes over time
const context = (initialSummary) => ({
  summary: initialSummary || null,
  error: null
});

// 2. Services: The async function to get the AI summary
const fetchSummaryService = async (ctx, event) => {
  // Replace this with your actual API call from useSummary
  const response = await fetch(`/api/summarize?url=${event.url}`);
  const json = await response.json();
  if (!response.ok) throw new Error(json.error);
  return json; // Expecting { html: "..." }
};

// 3. The Machine
export const articleMachine = createMachine({
  // STATE 1: Unread (Default)
  unread: state(
    transition('READ', 'read'),
    transition('GENERATE', 'generating'),
    transition('REMOVE', 'removed'),
    transition('TOGGLE_EXPAND', 'generating') // If they click expand but no summary exists, generate it
  ),

  // STATE 2: Generating (Async Loading)
  generating: invoke(fetchSummaryService,
    transition('done', 'expanded',
      reduce((ctx, ev) => ({ ...ctx, summary: ev.data.html }))
    ),
    transition('error', 'unread', // Fallback to unread on error, or a dedicated error state
      reduce((ctx, ev) => ({ ...ctx, error: ev.error }))
    ),
    transition('REMOVE', 'removed') // User can delete even while loading!
  ),

  // STATE 3: Read (Collapsed)
  // Has summary data, but hidden
  read: state(
    transition('TOGGLE_EXPAND', 'expanded'),
    transition('REMOVE', 'removed')
  ),

  // STATE 4: Expanded (Visible Summary)
  // Implies it is also "Read"
  expanded: state(
    transition('TOGGLE_EXPAND', 'read'), // Collapsing goes back to "read" state
    transition('REMOVE', 'removed')
  ),

  // STATE 5: Removed (Final)
  // We allow 'RESTORE' if you want undo functionality
  removed: state(
    transition('RESTORE', 'unread') 
  )
}, context);

2. The Implementation (ArticleCard.jsx)
Notice how much logic disappears from the component body. We don't check !isRemoved && isAvailable anymore. We just ask the machine "Can I do this?" or "What state are we in?".
import { useMachine } from 'react-robot'; // You'll need this package
import { articleMachine } from './articleMachine';
import { CheckCircle, Loader2, Minus, Sparkles, Trash2 } from 'lucide-react';

function ArticleCard({ article }) {
  // Initialize machine. Pass initial context if you have cached data.
  const [current, send] = useMachine(articleMachine, { 
    summary: article.cachedSummary 
  });
  
  // Helper booleans derived directly from state
  // No more combining isRead && !isRemoved manually
  const isRemoved = current.matches('removed');
  const isGenerating = current.matches('generating');
  const isExpanded = current.matches('expanded');
  const isRead = current.matches('read') || isExpanded; // Expanded implies read
  const hasSummary = !!current.context.summary;

  // --- Handlers are now just signals ---

  const handleMainClick = (e) => {
    if (isRemoved) return; // Optional: could also be handled by machine ignoring event
    
    // Logic: If we have a summary, toggle it. If not, just mark read.
    if (hasSummary) {
        send('TOGGLE_EXPAND');
    } else {
        send('READ');
    }
  };

  const handleTldrClick = (e) => {
    e.stopPropagation();
    // One signal handles "Generate" OR "Expand" OR "Collapse" based on current state
    send({ type: 'TOGGLE_EXPAND', url: article.url });
  };

  const handleRemove = (e) => {
    e.stopPropagation();
    send('REMOVE');
  };

  return (
    <div
      onClick={handleMainClick}
      data-state={current.name} // Great for CSS styling/debugging
      className={`
        group relative transition-all duration-300 ease-out rounded-[20px] border
        ${isGenerating ? 'opacity-80 bg-slate-50' : ''}
        ${isRemoved 
            ? 'opacity-50 grayscale scale-[0.95] bg-slate-50 border-transparent' 
            : 'bg-white/80 hover:shadow-lg cursor-pointer'}
        ${isExpanded ? 'ring-1 ring-brand-100 shadow-md bg-white mb-6' : 'mb-3'}
      `}
    >
      <div className="p-5 flex flex-col gap-2">
        
        {/* Title */}
        <h3 className={`text-[17px] font-semibold ${isRead ? 'text-slate-500 font-normal' : 'text-slate-900'}`}>
          {article.title}
        </h3>

        {/* Action Bar - Only show if not removed */}
        {!isRemoved && (
          <div className="flex items-center justify-between pt-3">
            
            {/* The Magic TLDR Button */}
            <button
              onClick={handleTldrClick}
              disabled={isGenerating}
              className={`
                flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold
                ${isGenerating ? 'bg-slate-50 text-slate-400' : ''}
                ${isExpanded ? 'bg-slate-100 text-slate-600' : 'bg-indigo-50 text-indigo-600'}
              `}
            >
              {isGenerating ? <Loader2 size={14} className="animate-spin" /> : 
               isExpanded ? <><Minus size={14} /> Close</> : 
               <><Sparkles size={14} /> {hasSummary ? 'View TLDR' : 'Generate TLDR'}</>
              }
            </button>

            <button onClick={handleRemove} className="text-slate-400 hover:text-red-500">
              <Trash2 size={14} />
            </button>
          </div>
        )}

        {/* Summary Content */}
        {isExpanded && (
           <div className="animate-fade-in mt-4 border-t border-slate-100 pt-5">
              <div 
                className="prose prose-sm text-slate-600"
                dangerouslySetInnerHTML={{ __html: current.context.summary }} 
              />
           </div>
        )}
      </div>
    </div>
  );
}

Why this is better for your code:
 * Unified Async Logic: You don't need to check if (loading) inside your remove handler. If the user clicks remove while the AI is generating, the machine transitions to removed. The generating service (the fetch) is automatically cancelled or its result ignored because the machine has moved on.
 * No more useEffect dependencies: You aren't watching isRead to trigger something else. The state is the source of truth.
 * Expansion Logic: In the machine, I set it so TOGGLE_EXPAND works differently depending on if we have data. If we are unread, it triggers generating. If we are read (and have data), it simply expands. The UI button just sends TOGGLE_EXPAND regardless.
