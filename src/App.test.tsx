import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the scaffold messaging', () => {
    render(<App />);
    expect(screen.getByText(/visualization playground/i)).toBeInTheDocument();
  });
});
