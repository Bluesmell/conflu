import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import MermaidNodeView from '../../components/editor/nodeviews/MermaidNodeView'; // To be created

export interface MermaidDiagramOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    mermaidDiagram: {
      /**
       * Add a mermaidDiagram node
       */
      setMermaidDiagram: (attributes?: { syntax?: string }) => ReturnType;
      /**
       * Update mermaidDiagram node
       */
      updateMermaidDiagram: (attributes: { syntax: string }) => ReturnType;
    };
  }
}

export default Node.create<MermaidDiagramOptions>({
  name: 'mermaidDiagram',
  group: 'block',
  atom: true, // Treat as a single unit
  draggable: true,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      syntax: {
        default: 'graph TD\nA-->B', // Default diagram
        parseHTML: element => element.querySelector('pre[data-mermaid-syntax]')?.textContent || 'graph TD\nA-->B',
        renderHTML: attributes => {
          // Store syntax in a <pre> tag within the main div for SSR or non-JS environments
          // The actual rendering will be handled by the NodeView on the client.
          // This also helps in copying/pasting the raw syntax.
          return { 'data-mermaid-syntax-present': 'true' }; // Attribute to mark node
        },
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: `div[data-type="${this.name}"]`,
        // getAttrs defined in addAttributes via parseHTML
        // Content of pre tag is used to get syntax by addAttributes.parseHTML
      },
    ];
  },

  renderHTML({ HTMLAttributes, node }) {
    const syntax = node.attrs.syntax || '';
    return [
      'div',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, { 'data-type': this.name }),
      ['pre', { 'data-mermaid-syntax': 'true', style: 'display:none;' }, syntax], // Store syntax, hidden by default if JS active
      ['div', { class: 'mermaid-diagram-placeholder-ssr' }, `Loading Mermaid Diagram...\n${syntax}`] // Placeholder for SSR/no-JS
    ];
  },

  addCommands() {
    return {
      setMermaidDiagram: (attributes) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: attributes,
        });
      },
      updateMermaidDiagram: (attributes) => ({ commands }) => {
        return commands.updateAttributes(this.name, attributes);
      }
    };
  },

  addNodeView() {
    return ReactNodeViewRenderer(MermaidNodeView);
  },
});
