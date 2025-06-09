import { Schema } from '@tiptap/pm/model';

export const appSchema = new Schema({
  nodes: {
    doc: {
      content: 'block+',
    },
    paragraph: {
      content: 'inline*',
      group: 'block',
      parseDOM: [{ tag: 'p' }],
      toDOM() {
        return ['p', 0];
      },
    },
    text: {
      group: 'inline',
    },
    heading: {
      attrs: { level: { default: 1 } },
      content: 'inline*',
      group: 'block',
      defining: true,
      parseDOM: [
        { tag: 'h1', attrs: { level: 1 } },
        { tag: 'h2', attrs: { level: 2 } },
        { tag: 'h3', attrs: { level: 3 } },
        // Add h4, h5, h6 if needed later
      ],
      toDOM(node) {
        return [`h${node.attrs.level}`, 0];
      },
    },
    bulletList: {
      content: 'listItem+',
      group: 'block',
      parseDOM: [{ tag: 'ul' }],
      toDOM() {
        return ['ul', 0];
      },
    },
    orderedList: {
      content: 'listItem+',
      group: 'block',
      parseDOM: [{ tag: 'ol' }],
      toDOM() {
        return ['ol', 0];
      },
    },
    listItem: {
      content: 'paragraph block*', // Allow paragraphs and other blocks within list items
      defining: true,
      parseDOM: [{ tag: 'li' }],
      toDOM() {
        return ['li', 0];
      },
    },
  },
  marks: {
    bold: {
      parseDOM: [
        { tag: 'strong' },
        { style: 'font-weight', getAttrs: (value: string | NodeJS.StyleDeclaration) => typeof value === 'string' && /^(bold(er)?|[5-9]\d{2,})$/.test(value) && null },
      ],
      toDOM() {
        return ['strong', 0];
      },
    },
    italic: {
      parseDOM: [
        { tag: 'em' },
        { tag: 'i' },
        { style: 'font-style=italic' },
      ],
      toDOM() {
        return ['em', 0];
      },
    },
    link: {
      attrs: {
        href: {},
        title: { default: null },
        target: { default: '_blank'} // Default to open in new tab
      },
      inclusive: false,
      parseDOM: [
        {
          tag: 'a[href]',
          getAttrs: (dom: HTMLElement | string) => {
            if (typeof dom === 'string') return {}; // Should not happen with 'a[href]'
            return { href: dom.getAttribute('href'), title: dom.getAttribute('title'), target: dom.getAttribute('target') };
          },
        },
      ],
      toDOM(node) {
        const { href, title, target } = node.attrs;
        return ['a', { href, title, target }, 0];
      },
    },
  },
});

export default appSchema;
