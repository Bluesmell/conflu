import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import FallbackMacroNodeView from '../../components/editor/nodeviews/FallbackMacroNodeView';

export interface FallbackMacroPlaceholderOptions {
  HTMLAttributes: Record<string, any>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    fallbackMacroPlaceholder: {
      /**
       * Add a fallbackMacroPlaceholder node
       */
      setFallbackMacroPlaceholder: (attributes: { macroName: string; fallbackMacroId: number }) => ReturnType;
    };
  }
}

export default Node.create<FallbackMacroPlaceholderOptions>({
  name: 'fallbackMacroPlaceholder',
  group: 'block', // Or 'inline' if preferred, but block is common for placeholders
  atom: true, // Important: treats the node as a single, indivisible unit
  draggable: true,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      macroName: {
        default: 'Unknown Macro',
        parseHTML: element => element.getAttribute('data-macro-name'),
        renderHTML: attributes => ({ 'data-macro-name': attributes.macroName }),
      },
      fallbackMacroId: {
        default: null,
        parseHTML: element => {
          const id = element.getAttribute('data-fallback-id');
          return id ? parseInt(id, 10) : null;
        },
        renderHTML: attributes => ({ 'data-fallback-id': attributes.fallbackMacroId }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: `div[data-type="${this.name}"]`, // Use this.name for robustness
        // getAttrs defined in addAttributes via parseHTML
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    // HTMLAttributes already includes what's defined in addAttributes' renderHTML
    return ['div', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, { 'data-type': this.name })];
  },

  addCommands() {
    return {
      setFallbackMacroPlaceholder: attributes => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: attributes,
        });
      },
    };
  },

  addNodeView() {
    return ReactNodeViewRenderer(FallbackMacroNodeView);
  },
});
