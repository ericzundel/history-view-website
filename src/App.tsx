import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';
import './App.css';

const highlights = [
  'Bubble heatmap landing view driven by level0.json',
  'Animated treemap overlays with category drill-downs',
  'Client-side routing to mock pages for palette and layout exploration'
];

const checklist = [
  'Wire data loaders to emit level0/level1 JSON + sprites',
  'Design the bubble heatmap and overlay interactions',
  'Connect deployment script to publish static assets'
];

function App() {
  return (
    <main className="app">
      <header className="hero">
        <div className="logo-row">
          <a href="https://vitejs.dev" target="_blank" rel="noreferrer">
            <img src={viteLogo} className="logo" alt="Vite logo" />
          </a>
          <a href="https://react.dev" target="_blank" rel="noreferrer">
            <img src={reactLogo} className="logo react" alt="React logo" />
          </a>
        </div>
        <div>
          <p className="eyebrow">History View</p>
          <h1>Visualization playground</h1>
          <p className="lede">
            Fresh Vite + TypeScript scaffold ready for building the browsing history explorer.
            Start by wiring the data loaders, then iterate on the bubble heatmap and treemap
            overlays.
          </p>
        </div>
      </header>

      <section className="panel">
        <h2>Coming up next</h2>
        <ul className="pill-list">
          {highlights.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2>Build checklist</h2>
        <ol className="checklist">
          {checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      </section>
    </main>
  );
}

export default App;
