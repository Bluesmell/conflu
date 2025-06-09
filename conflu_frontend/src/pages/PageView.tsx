import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPageDetails } from '../services/api';
import { Page } from '../types/apiModels';
import RenderedPageContent from '../components/content/RenderedPageContent'; // We'll create this next

const PageView: React.FC = () => {
  const { spaceKey, pageId } = useParams<{ spaceKey: string; pageId: string }>();
  const [page, setPage] = useState<Page | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pageId) {
      setError('Page ID is missing from URL.');
      setIsLoading(false);
      return;
    }
    // spaceKey is available if needed for context, e.g. breadcrumbs, but fetchPageDetails uses pageId

    const loadPageData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        // Ensure pageId is a string or number as expected by your API client
        const pageDetails = await fetchPageDetails(pageId);
        setPage(pageDetails);
      } catch (err) {
        setError(`Failed to load page ID "${pageId}".`);
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadPageData();
  }, [pageId]);

  if (isLoading) {
    return <p>Loading page content...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  if (!page) {
    return <p>Page not found.</p>;
  }

  return (
    <div>
      <h1>{page.title}</h1>
      {/* We will pass page.raw_content to RenderedPageContent */}
      <RenderedPageContent rawContent={page.raw_content} />
    </div>
  );
};

export default PageView;
