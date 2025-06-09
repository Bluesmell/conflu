import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchSpaceDetails, fetchPagesInSpace } from '../services/api';
import { Space, Page } from '../types/apiModels';

const SpaceView: React.FC = () => {
  const { spaceKey } = useParams<{ spaceKey: string }>();
  const [space, setSpace] = useState<Space | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!spaceKey) {
      setError('Space key is missing from URL.');
      setIsLoading(false);
      return;
    }

    const loadSpaceData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const spaceDetails = await fetchSpaceDetails(spaceKey);
        setSpace(spaceDetails);
        const spacePages = await fetchPagesInSpace(spaceKey);
        setPages(spacePages);
      } catch (err) {
        setError(`Failed to load space "${spaceKey}".`);
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadSpaceData();
  }, [spaceKey]);

  if (isLoading) {
    return <p>Loading space details...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  if (!space) {
    return <p>Space not found.</p>;
  }

  return (
    <div>
      <h1>{space.name}</h1>
      {space.description && <p>{space.description}</p>}

      <h2>Pages in this Space</h2>
      {pages.length === 0 ? (
        <p>No pages found in this space.</p>
      ) : (
        <ul>
          {pages.map((page) => (
            <li key={page.id}>
              <Link to={`/spaces/${spaceKey}/pages/${page.id}`}>{page.title}</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SpaceView;
