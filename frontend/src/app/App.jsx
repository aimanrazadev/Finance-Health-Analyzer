import { BrowserRouter } from 'react-router-dom';
import Providers from './providers';
import AppRouter from './router';
import '../styles/App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Providers>
        <AppRouter />
      </Providers>
    </BrowserRouter>
  );
}
