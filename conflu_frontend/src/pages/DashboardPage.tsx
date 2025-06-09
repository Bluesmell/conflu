import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchSpaces } from '../services/api';
import { Space } from '../types/apiModels';

const DashboardPage: React.FC = () => {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSpaces = async () => {
      try {
        setIsLoading(true);
        const fetchedSpaces = await fetchSpaces();
        setSpaces(fetchedSpaces);
        setError(null);
      } catch (err) {
        setError('Failed to load spaces.');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    loadSpaces();
  }, []);

  if (isLoading) {
    return <p>Loading spaces...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  return (
    <div>
      <h1>Welcome to Conflu</h1>
      <h2>Spaces</h2>
      {spaces.length === 0 ? (
        <p>No spaces available. You can create one if you have permissions.</p>
      ) : (
        <ul>
          {spaces.map((space) => (
            <li key={space.key}>
              <Link to={`/spaces/${space.key}`}>
                <strong>{space.name}</strong> ({space.key})
              </Link>
              {space.description && <p>{space.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DashboardPage;
