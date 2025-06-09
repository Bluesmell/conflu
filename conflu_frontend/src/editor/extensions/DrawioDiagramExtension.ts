import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import DrawioNodeView from '../../components/editor/nodeviews/DrawioNodeView'; // To be created

export interface DrawioDiagramOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    drawioDiagram: {
      /**
       * Add a drawioDiagram node
       */
      setDrawioDiagram: (attributes?: { xml?: string }) => ReturnType;
      /**
       * Update drawioDiagram node's XML
       */
      updateDrawioDiagramXml: (attributes: { xml: string }) => ReturnType;
    };
  }
}

export default Node.create<DrawioDiagramOptions>({
  name: 'drawioDiagram',
  group: 'block',
  atom: true,
  draggable: true,

  addOptions() {
    return {
      HTMLAttributes: {}, // For the outer div rendered by renderHTML
    };
  },

  addAttributes() {
    return {
      xml: {
        default: '',
        // parseHTML and renderHTML for attributes are handled by the main parseHTML/renderHTML if needed
        // For complex data like XML, it's often better to store it within a child <pre> or similar,
        // or handle it entirely within the NodeView and only use a placeholder in renderHTML.
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: `div[data-type="${this.name}"]`,
        getAttrs: (dom: HTMLElement) => {
          // Attempt to get XML from a hidden <pre> tag, similar to Mermaid extension
          const preElement = dom.querySelector('pre[data-drawio-xml]');
          const xml = preElement ? preElement.textContent : '';
          return { xml: xml || '' };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes, node }) {
    // This HTML is mainly for SSR, copy-paste, or when JS is disabled.
    // The NodeView will take over rendering on the client.
    // Store XML in a hidden <pre> tag to make it available for parseHTML and copy-paste.
    const xml = node.attrs.xml || '';
    return [
      'div',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, { 'data-type': this.name }),
      ['pre', { 'data-drawio-xml': 'true', style: 'display:none;' }, xml],
      ['div', { class: 'drawio-diagram-placeholder-ssr' }, '[Draw.io Diagram - Requires JavaScript to view and edit]']
    ];
  },

  addCommands() {
    return {
      setDrawioDiagram: (attributes) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: attributes,
        });
      },
      updateDrawioDiagramXml: (attributes) => ({ commands }) => {
        // This command assumes the node is already selected or position is known.
        // Typically, updateAttributes is called from within the NodeView itself
        // where the node's position is known.
        return commands.updateAttributes(this.name, attributes);
      },
    };
  },

  addNodeView() {
    return ReactNodeViewRenderer(DrawioNodeView);
  },
});
