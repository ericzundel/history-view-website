import './App.css';
import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

type Level0Entry = {
  day: number;
  hour: number;
  value: number;
  size: number;
};

type Level1Site = {
  title: string;
  url: string;
  domain?: string;
  value: number;
  favicon_symbol_id?: string;
};

type Level1Category = {
  tag: string;
  label: string;
  value: number;
  sites: Level1Site[];
};

type Level1Data = {
  day: number;
  hour: number;
  categories: Level1Category[];
  uncategorized: Level1Category[];
};

type SelectedCell = {
  day: number;
  hour: number;
  value: number;
};

const dayLabels = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const hours = Array.from({ length: 24 }, (_, hour) => hour);
const colorScale = [
  '#2f1b12',
  '#4a2414',
  '#6b2c13',
  '#8a3b19',
  '#a84e24',
  '#c96030',
  '#dd7b44',
  '#e99a63',
  '#f3b989',
  '#f6cda5',
  '#f8dfc3',
  '#fbf0e1',
];

const CATEGORY_SPAN_DIVISOR = 40;
const SITE_SPAN_DIVISOR = 30;

const formatHourLabel = (hour: number) => `${String(hour).padStart(2, '0')}:00`;

const buildFallbackLevel0 = (): Level0Entry[] => {
  const entries: Level0Entry[] = [];
  for (let day = 0; day < 7; day += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const base = Math.max(0, 12 - Math.abs(12 - hour));
      const wave = 10 + Math.sin((day / 7) * Math.PI * 2) * 8;
      const value = Math.max(0, Math.round((base + wave) * (day % 2 === 0 ? 1.2 : 0.85)));
      const size = Math.min(100, Math.round((value / 24) * 100));
      if (value > 6) {
        entries.push({ day, hour, value, size });
      }
    }
  }
  return entries;
};

const buildFallbackLevel1 = (day: number, hour: number): Level1Data => ({
  day,
  hour,
  categories: [
    {
      tag: '#news',
      label: 'News',
      value: 142,
      sites: [
        { title: 'Local Dispatch', url: 'https://example.com/news', value: 42 },
        { title: 'World Bulletin', url: 'https://example.com/world', value: 34 },
        { title: 'Tech Ledger', url: 'https://example.com/tech', value: 66 },
      ],
    },
    {
      tag: '#tools',
      label: 'Tools',
      value: 96,
      sites: [
        { title: 'Docs Studio', url: 'https://example.com/docs', value: 40 },
        { title: 'Issue Tracker', url: 'https://example.com/issues', value: 28 },
        { title: 'Commit Logs', url: 'https://example.com/commits', value: 28 },
      ],
    },
    {
      tag: '#video',
      label: 'Video',
      value: 72,
      sites: [
        { title: 'Archive Clips', url: 'https://example.com/clips', value: 30 },
        { title: 'Studio Archive', url: 'https://example.com/archive', value: 24 },
        { title: 'History Talks', url: 'https://example.com/talks', value: 18 },
      ],
    },
    {
      tag: '#social',
      label: 'Community',
      value: 54,
      sites: [
        { title: 'Friends Feed', url: 'https://example.com/feed', value: 22 },
        { title: 'Group Threads', url: 'https://example.com/threads', value: 18 },
        { title: 'Forum Notes', url: 'https://example.com/forum', value: 14 },
      ],
    },
  ],
  uncategorized: [],
});

const normalizeLevel0 = (entries: unknown): Level0Entry[] => {
  if (!Array.isArray(entries)) {
    return [];
  }
  return entries
    .map((entry) => {
      if (typeof entry !== 'object' || entry === null) {
        return null;
      }
      const record = entry as Record<string, string | number>;
      const day = Number(record.day);
      const hour = Number(record.hour);
      const value = Number(record.value);
      const size = Number(record.size);
      if (Number.isNaN(day) || Number.isNaN(hour) || Number.isNaN(value) || Number.isNaN(size)) {
        return null;
      }
      return { day, hour, value, size };
    })
    .filter((entry): entry is Level0Entry => entry !== null);
};

function App() {
  const [level0, setLevel0] = useState<Level0Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [useFallback, setUseFallback] = useState(false);
  const [selectedCell, setSelectedCell] = useState<SelectedCell | null>(null);
  const [level1, setLevel1] = useState<Level1Data | null>(null);
  const [level1Loading, setLevel1Loading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<Level1Category | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const loadLevel0 = async () => {
      try {
        const response = await fetch('/data/viz_data/level0.json', {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error('Unable to load level0 data');
        }
        const payload = await response.json();
        const normalized = normalizeLevel0(payload);
        if (active) {
          if (normalized.length === 0) {
            setLevel0(buildFallbackLevel0());
            setUseFallback(true);
          } else {
            setLevel0(normalized);
            setUseFallback(false);
          }
        }
      } catch {
        if (active) {
          setLevel0(buildFallbackLevel0());
          setUseFallback(true);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadLevel0();

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selectedCell) {
      setLevel1(null);
      setSelectedCategory(null);
      return;
    }

    let active = true;
    const controller = new AbortController();
    const loadLevel1 = async () => {
      setLevel1Loading(true);
      const paddedHour = String(selectedCell.hour).padStart(2, '0');
      const candidates = [
        `/data/viz_data/level1-${selectedCell.day}-${paddedHour}.json`,
        `/data/viz_data/level1-${selectedCell.day}-${selectedCell.hour}.json`,
      ];

      for (const url of candidates) {
        try {
          const response = await fetch(url, { signal: controller.signal });
          if (!response.ok) {
            continue;
          }
          const payload = (await response.json()) as Level1Data;
          if (active) {
            setLevel1(payload);
            setSelectedCategory(payload.categories[0] ?? null);
          }
          return;
        } catch {
          if (!active) {
            return;
          }
        }
      }

      if (active) {
        const fallback = buildFallbackLevel1(selectedCell.day, selectedCell.hour);
        setLevel1(fallback);
        setSelectedCategory(fallback.categories[0] ?? null);
      }
    };

    loadLevel1().finally(() => {
      if (active) {
        setLevel1Loading(false);
      }
    });

    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedCell]);

  useEffect(() => {
    if (!selectedCell) {
      return undefined;
    }
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedCell(null);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [selectedCell]);

  const entryMap = useMemo(() => {
    const map = new Map<string, Level0Entry>();
    level0.forEach((entry) => {
      map.set(`${entry.day}-${entry.hour}`, entry);
    });
    return map;
  }, [level0]);

  const maxValue = useMemo(() => {
    if (level0.length === 0) {
      return 0;
    }
    return level0.reduce((max, entry) => Math.max(max, entry.value), 0);
  }, [level0]);

  return (
    <main className="heatmap-app">
      <header className="topbar">
        <div className="title-block">
          <p className="eyebrow">History View</p>
          <h1>Browsing rhythm heatmap</h1>
          <p className="subtitle">
            Hover any bubble to reveal visit volume. Click a cell to open the category treemap and
            drill into the sites behind that hour.
          </p>
          {useFallback ? (
            <p className="fallback-note">
              Sample data is displayed. Add <code>data/viz_data/level0.json</code> to see live results.
            </p>
          ) : null}
        </div>
        <div className="legend">
          <div>
            <p className="legend-title">Legend</p>
            <p className="legend-copy">
              Bubble size mirrors visit count. Darker hues indicate heavier activity. Click any hour
              to open the overlay.
            </p>
          </div>
          <a
            className="github-link"
            href="https://github.com/ericzundel/history-view-website"
            target="_blank"
            rel="noreferrer"
            aria-label="History View repository on GitHub"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M12 2C6.48 2 2 6.59 2 12.26c0 4.5 2.87 8.32 6.84 9.67.5.1.68-.22.68-.48 0-.24-.01-.88-.01-1.72-2.78.62-3.37-1.37-3.37-1.37-.45-1.2-1.1-1.52-1.1-1.52-.9-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.58 2.36 1.12 2.94.86.09-.67.35-1.12.64-1.38-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.71 0 0 .85-.28 2.78 1.05.8-.23 1.66-.35 2.52-.35.86 0 1.72.12 2.52.35 1.93-1.33 2.78-1.05 2.78-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.57 5.06.36.33.68.96.68 1.95 0 1.41-.01 2.55-.01 2.9 0 .26.18.58.69.48 3.96-1.35 6.83-5.17 6.83-9.67C22 6.59 17.52 2 12 2z" />
            </svg>
          </a>
        </div>
      </header>

      <section className={`heatmap-stage ${selectedCell ? 'is-dimmed' : ''}`}>
        <div className="heatmap-scroll">
          <div className={`heatmap-grid ${loading ? '' : 'is-ready'}`}>
            <div className="grid-corner" />
            {hours.map((hour) => (
              <div className="hour-label" key={`hour-${hour}`}>
                {formatHourLabel(hour)}
              </div>
            ))}
            {dayLabels.map((dayLabel, dayIndex) => (
              <div className="heatmap-row" key={`day-${dayLabel}`}>
                <div className="day-label">{dayLabel}</div>
                {hours.map((hour) => {
                  const entry = entryMap.get(`${dayIndex}-${hour}`);
                  const value = entry?.value ?? 0;
                  const size = entry?.size ?? 0;
                  const intensity = maxValue > 0 ? value / maxValue : 0;
                  const colorIndex = Math.min(
                    colorScale.length - 1,
                    Math.floor(intensity * colorScale.length)
                  );
                  const bubbleSize = 10 + Math.round((size / 100) * 42);
                  return (
                    <button
                      key={`cell-${dayIndex}-${hour}`}
                      className="heatmap-cell"
                      type="button"
                      onClick={() => setSelectedCell({ day: dayIndex, hour, value: value || 0 })}
                      aria-label={`${dayLabel} at ${formatHourLabel(hour)} with ${value} visits`}
                    >
                      <span
                        className="bubble"
                        style={
                          {
                            '--bubble-size': `${bubbleSize}px`,
                            '--bubble-color': colorScale[colorIndex],
                            '--bubble-alpha': `${Math.max(0.2, intensity)}`,
                          } as CSSProperties
                        }
                      />
                      <span className="bubble-tooltip">
                        <span>{dayLabel}</span>
                        <span>{formatHourLabel(hour)}</span>
                        <span className="bubble-value">
                          {value > 0 ? `${value.toLocaleString()} visits` : 'No visits'}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </section>

      {selectedCell ? (
        <div className="overlay" role="dialog" aria-modal="true">
          <div className="overlay-panel">
            <div className="overlay-header">
              <div>
                <p className="overlay-kicker">Heatmap drill-down</p>
                <h2>
                  {dayLabels[selectedCell.day]} · {formatHourLabel(selectedCell.hour)}
                </h2>
                <p className="overlay-subtitle">
                  {selectedCell.value.toLocaleString()} visits during this hour.
                </p>
              </div>
              <button
                className="overlay-close"
                type="button"
                aria-label="Close heatmap drill-down dialog"
                onClick={() => setSelectedCell(null)}
              >
                Close
              </button>
            </div>
            <div className="overlay-content">
              <section className="overlay-section">
                <div className="section-header">
                  <h3>Categories</h3>
                  <p>Select a category to view the most visited sites.</p>
                </div>
                {level1Loading ? (
                  <div className="skeleton">Loading categories…</div>
                ) : level1?.categories.length ? (
                  <div className="treemap">
                    {level1.categories.map((category) => (
                      <button
                        key={category.tag}
                        className={`treemap-tile ${
                          selectedCategory?.tag === category.tag ? 'is-active' : ''
                        }`}
                        type="button"
                        onClick={() => setSelectedCategory(category)}
                        style={
                          {
                            gridColumn: `span ${Math.min(
                              4,
                              Math.max(1, Math.round(category.value / CATEGORY_SPAN_DIVISOR))
                            )}`,
                          } as CSSProperties
                        }
                      >
                        <span>{category.label}</span>
                        <span className="tile-meta">{category.value}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    No categories yet. Classification data will appear here once built.
                  </div>
                )}
              </section>
              <section className="overlay-section">
                <div className="section-header">
                  <h3>Sites</h3>
                  <p>Sites inside the selected category. Click to visit.</p>
                </div>
                {selectedCategory ? (
                  <div className="treemap sites">
                    {selectedCategory.sites.map((site) => (
                      <a
                        key={site.url}
                        href={site.url}
                        className="treemap-tile"
                        style={
                          {
                            gridColumn: `span ${Math.min(
                              3,
                              Math.max(1, Math.round(site.value / SITE_SPAN_DIVISOR))
                            )}`,
                          } as CSSProperties
                        }
                        target="_blank"
                        rel="noreferrer"
                      >
                        <span>{site.title}</span>
                        <span className="tile-meta">{site.value}</span>
                      </a>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">Pick a category to populate this treemap.</div>
                )}
              </section>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

export default App;
