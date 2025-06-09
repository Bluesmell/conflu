import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import SpaceView from './pages/SpaceView';
import PageView from './pages/PageView';
import EditorView from './pages/EditorView';
import SearchResultsView from './pages/SearchResultsView';
import SpaceSettingsPage from './pages/SpaceSettingsPage';
import ConfluenceImportPage from './pages/ConfluenceImportPage';
import ImportStatusPage from './pages/ImportStatusPage';
import NotFoundPage from './pages/NotFoundPage';
import './App.css'; // General app styles
import './styles/RenderedContent.css'; // Styles for Tiptap rendered HTML

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="spaces/:spaceKey" element={<SpaceView />} />
          {/* Page View */}
          <Route path="spaces/:spaceKey/pages/:pageId" element={<PageView />} />
          {/* Page Edit */}
          <Route path="spaces/:spaceKey/pages/:pageId/edit" element={<EditorView />} />
          {/* New Page in Space (optional parent via query param ?parent=parentId) */}
          <Route path="spaces/:spaceKey/pages/new" element={<EditorView />} />
          {/* Search Results Page */}
          <Route path="search" element={<SearchResultsView />} />
          {/* Space Settings Page */}
          <Route path="spaces/:spaceKey/settings" element={<SpaceSettingsPage />} />
          {/* Import Confluence Page */}
          <Route path="import/confluence" element={<ConfluenceImportPage />} />
          {/* Import Status Page - ensure this route is also defined if not already */}
          <Route path="import/status/:uploadId" element={<ImportStatusPage />} />
          {/* Optional: More specific settings routes like /spaces/:spaceKey/settings/permissions */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
