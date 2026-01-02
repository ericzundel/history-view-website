import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import { normalizeLevel0 } from './app-utils';

describe('App', () => {
  const mockFetch = (responses: Array<{ ok: boolean; json: () => Promise<unknown> }>) => {
    const fetchMock = vi.fn();
    responses.forEach((response) => {
      fetchMock.mockImplementationOnce(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0));
        return response;
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  };

  const nextTick = () => new Promise((resolve) => setTimeout(resolve, 0));

  const renderApp = async () => {
    await act(async () => {
      render(<App />);
      await nextTick();
    });
  };

  const flushEffects = async () => {
    await act(async () => {
      await nextTick();
    });
  };

  const clickAndFlush = async (user: ReturnType<typeof userEvent.setup>, element: Element) => {
    await act(async () => {
      await user.click(element);
      await nextTick();
    });
  };

  const escapeAndFlush = async (user: ReturnType<typeof userEvent.setup>) => {
    await act(async () => {
      await user.keyboard('{Escape}');
      await nextTick();
    });
  };

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows fallback data when level0 cannot load', async () => {
    mockFetch([
      {
        ok: false,
        json: async () => [],
      },
    ]);

    await renderApp();

    expect(await screen.findByText(/sample data is displayed/i)).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('heading', { name: /browsing rhythm heatmap/i })).toBeInTheDocument();
    await flushEffects();
  });

  it('renders level0 bubbles and opens overlay on click', async () => {
    mockFetch([
      {
        ok: true,
        json: async () => [
          { day: 0, hour: 1, value: 2, size: 60 },
          { day: 1, hour: 14, value: 4, size: 80 },
        ],
      },
      {
        ok: true,
        json: async () => ({
          day: 0,
          hour: 1,
          categories: [
            {
              tag: '#news',
              label: 'News',
              value: 2,
              sites: [{ title: 'Example', url: 'https://example.com', value: 2 }],
            },
          ],
          uncategorized: [],
        }),
      },
    ]);

    const user = userEvent.setup();
    await renderApp();

    const target = await screen.findByRole('button', {
      name: /sunday at 01:00 with 2 visits/i,
    });
    await clickAndFlush(user, target);

    expect(await screen.findByRole('heading', { name: /sunday · 01:00/i })).toBeInTheDocument();
    expect(screen.getByText(/2 visits during this hour/i)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /news/i })).toBeInTheDocument();
    await flushEffects();
  });

  it('tries padded then unpadded level1 filenames', async () => {
    const fetchMock = mockFetch([
      {
        ok: true,
        json: async () => [{ day: 0, hour: 1, value: 3, size: 90 }],
      },
      {
        ok: false,
        json: async () => ({}),
      },
      {
        ok: true,
        json: async () => ({
          day: 0,
          hour: 1,
          categories: [],
          uncategorized: [],
        }),
      },
    ]);

    const user = userEvent.setup();
    await renderApp();

    const target = await screen.findByRole('button', {
      name: /sunday at 01:00 with 3 visits/i,
    });
    await clickAndFlush(user, target);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/data/viz_data/level1-0-01.json', expect.anything());
      expect(fetchMock).toHaveBeenCalledWith('/data/viz_data/level1-0-1.json', expect.anything());
    });
    expect(await screen.findByText(/no categories yet/i)).toBeInTheDocument();
    await flushEffects();
  });

  it('switches site treemap when selecting a new category', async () => {
    mockFetch([
      {
        ok: true,
        json: async () => [{ day: 2, hour: 9, value: 5, size: 70 }],
      },
      {
        ok: true,
        json: async () => ({
          day: 2,
          hour: 9,
          categories: [
            {
              tag: '#news',
              label: 'News',
              value: 5,
              sites: [{ title: 'Morning Brief', url: 'https://news.test', value: 3 }],
            },
            {
              tag: '#tools',
              label: 'Tools',
              value: 4,
              sites: [{ title: 'Docs Studio', url: 'https://docs.test', value: 4 }],
            },
          ],
          uncategorized: [],
        }),
      },
    ]);

    const user = userEvent.setup();
    await renderApp();

    const target = await screen.findByRole('button', {
      name: /tuesday at 09:00 with 5 visits/i,
    });
    await clickAndFlush(user, target);

    expect(await screen.findByText(/morning brief/i)).toBeInTheDocument();

    await clickAndFlush(user, screen.getByRole('button', { name: /tools/i }));
    expect(await screen.findByText(/docs studio/i)).toBeInTheDocument();
    await flushEffects();
  });

  it('closes overlay on escape', async () => {
    mockFetch([
      {
        ok: true,
        json: async () => [{ day: 4, hour: 17, value: 8, size: 90 }],
      },
      {
        ok: true,
        json: async () => ({
          day: 4,
          hour: 17,
          categories: [],
          uncategorized: [],
        }),
      },
    ]);

    const user = userEvent.setup();
    await renderApp();

    const target = await screen.findByRole('button', {
      name: /thursday at 17:00 with 8 visits/i,
    });
    await clickAndFlush(user, target);

    expect(await screen.findByRole('heading', { name: /thursday · 17:00/i })).toBeInTheDocument();
    expect(await screen.findByText(/no categories yet/i)).toBeInTheDocument();

    await escapeAndFlush(user);

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /thursday · 17:00/i })).toBeNull();
    });
    await flushEffects();
  });

  describe('normalizeLevel0', () => {
    it('returns an empty array for non-array inputs', () => {
      expect(normalizeLevel0(null)).toEqual([]);
      expect(normalizeLevel0(undefined)).toEqual([]);
      expect(normalizeLevel0({})).toEqual([]);
      expect(normalizeLevel0('nope')).toEqual([]);
    });

    it('filters out malformed entries and non-numeric values', () => {
      expect(
        normalizeLevel0([
          null,
          {},
          { day: 'x', hour: 1, value: 2, size: 3 },
          { day: 0, hour: 'y', value: 2, size: 3 },
          { day: 0, hour: 1, value: 'z', size: 3 },
          { day: 0, hour: 1, value: 2, size: 'bad' },
        ])
      ).toEqual([]);
    });

    it('coerces numeric strings and drops entries with missing fields', () => {
      expect(
        normalizeLevel0([
          { day: '0', hour: '1', value: '10', size: '80' },
          { day: 2, hour: 3, value: 4, size: 50 },
          { day: 1, hour: 4, value: 2 },
          { day: 1, value: 2, size: 3 },
        ])
      ).toEqual([
        { day: 0, hour: 1, value: 10, size: 80 },
        { day: 2, hour: 3, value: 4, size: 50 },
      ]);
    });
  });
});
