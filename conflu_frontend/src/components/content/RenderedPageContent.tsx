import React from 'react';

interface RenderedPageContentProps {
  rawContent: any; // This will be ProseMirror JSON
}

// Helper function to render simple ProseMirror nodes.
// This is a very basic implementation for demonstration.
// A proper implementation would use Tiptap's generateHTML or a more robust renderer.
const renderNode = (node: any, index: number): JSX.Element | null => {
  if (!node) return null;

  switch (node.type) {
    case 'doc':
      return <>{node.content?.map(renderNode)}</>;
    case 'paragraph':
      return <p key={index}>{node.content?.map(renderNode)}</p>;
    case 'heading':
      const Tag = `h${node.attrs?.level || 1}` as keyof JSX.IntrinsicElements;
      return <Tag key={index}>{node.content?.map(renderNode)}</Tag>;
    case 'text':
      let textElement: React.ReactNode = node.text;
      if (node.marks) {
        node.marks.forEach((mark: any) => {
          if (mark.type === 'bold') {
            textElement = <strong>{textElement}</strong>;
          } else if (mark.type === 'italic') {
            textElement = <em>{textElement}</em>;
          }
          // Add more mark types as needed (underline, strike, etc.)
        });
      }
      return <span key={index}>{textElement}</span>;
    case 'bulletList':
      return <ul key={index}>{node.content?.map(renderNode)}</ul>;
    case 'listItem':
      return <li key={index}>{node.content?.map(renderNode)}</li>;
    // Add more node types as needed (e.g., orderedList, codeBlock, blockquote, image)
    default:
      console.warn('Unsupported node type:', node.type, node);
      return <span key={index}>[Unsupported content: {node.type}]</span>;
  }
};

const RenderedPageContent: React.FC<RenderedPageContentProps> = ({ rawContent }) => {
  if (!rawContent) {
    return <p>No content available.</p>;
  }

  // Assuming rawContent is already a JavaScript object (parsed JSON)
  // If it's a string, it should be parsed: JSON.parse(rawContent)
  // For now, the PageView component is expected to pass the parsed object.

  let contentToRender;
  if (typeof rawContent === 'string') {
    try {
      contentToRender = JSON.parse(rawContent);
    } catch (error) {
      console.error("Failed to parse rawContent JSON string:", error);
      return <pre style={{ color: 'red' }}>Error: Could not parse page content.</pre>;
    }
  } else if (typeof rawContent === 'object' && rawContent !== null) {
    contentToRender = rawContent;
  } else {
    return <pre style={{ color: 'orange' }}>Warning: Page content is not in a recognizable format.</pre>;
  }

  // Check if it's a valid ProseMirror document structure
  if (contentToRender.type !== 'doc' || !Array.isArray(contentToRender.content)) {
    console.warn("Content does not appear to be a valid ProseMirror document:", contentToRender);
    return (
        <div>
            <p style={{color: 'orange'}}>Content may not be structured as expected.</p>
            <pre>{JSON.stringify(contentToRender, null, 2)}</pre>
        </div>
    );
  }


  return (
    <div className="prose-mirror-render">
      {renderNode(contentToRender, 0)}
    </div>
  );
};

export default RenderedPageContent;
