import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Page } from '../../types/apiModels'; // Assuming Page has id, title, parent, and children (added by hierarchy processing)
import styles from './AppSidebar.module.css'; // Reuse sidebar styles or create a new one

export interface HierarchicalPage extends Page {
  children: HierarchicalPage[];
}

interface PageTreeItemProps {
  page: HierarchicalPage;
  level: number; // For indentation
}

const PageTreeItem: React.FC<PageTreeItemProps> = ({ page, level }) => {
  const [isExpanded, setIsExpanded] = useState(true); // Default to expanded, or load from user preference
  const { spaceKey, pageId: currentPageId } = useParams<{ spaceKey: string; pageId: string }>();

  const hasChildren = page.children && page.children.length > 0;

  const handleToggle = (event: React.MouseEvent) => {
    event.preventDefault(); // Prevent navigation if clicking on toggle icon
    event.stopPropagation();
    setIsExpanded(!isExpanded);
  };

  const isActive = String(page.id) === currentPageId;

  return (
    <li className={`${styles.pageTreeItem} ${isActive ? styles.activeSubItem : ''}`} style={{ paddingLeft: `${level * 15}px` }}>
      <div className={styles.pageLinkContainer}>
        {hasChildren && (
          <span onClick={handleToggle} className={styles.toggleIcon}>
            {isExpanded ? '▼' : '►'}
          </span>
        )}
        <Link to={`/spaces/${spaceKey}/pages/${page.id}`} title={page.title}>
          {page.title}
        </Link>
      </div>
      {hasChildren && isExpanded && (
        <ul className={styles.pageSubTree}>
          {page.children.map(childPage => (
            <PageTreeItem key={childPage.id} page={childPage} level={level + 1} />
          ))}
        </ul>
      )}
    </li>
  );
};

export default PageTreeItem;
