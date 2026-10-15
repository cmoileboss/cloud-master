import { Text } from '@mantine/core';
import DocumentsPage from './documents/DocumentsPage';

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <strong>FFK</strong>
          <span>Service des Grades</span>
        </div>
      </header>

      <main className="app-content">
        <DocumentsPage />
      </main>

      <footer className="app-footer">
        <Text size="xs" c="dimmed">
          Exercice de formation · Données et documents fictifs
        </Text>
      </footer>
    </div>
  );
}
