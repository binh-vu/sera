/**
 * TrieNode and Trie classes for managing a prefix tree structure
 * to efficiently store and retrieve words based on their prefixes.
 */
export class TrieNode {
  children: Map<string, TrieNode> = new Map();
  isEndOfWord: boolean = false;
  value: string = "";
}

/**
 * Trie (prefix tree) data structure for efficient string storage and retrieval.
 *
 * Provides O(m) insertion and O(m) lookup operations where m is the length of the string.
 * Optimized for prefix-based operations like longest prefix matching.
 */
export class Trie {
  root: TrieNode = new TrieNode();

  /**
   * Inserts a word into the trie structure.
   * Creates new nodes as needed along the path of characters.
   *
   * @param word - The string to insert into the trie
   */
  insert(word: string): void {
    let node = this.root;

    // Traverse/create path for each character in the word
    for (const char of word) {
      let nextNode = node.children.get(char);
      if (nextNode === undefined) {
        // Create new node if path doesn't exist
        nextNode = new TrieNode();
        node.children.set(char, nextNode);
      }
      node = nextNode;
    }

    // Mark the end of a complete word
    node.isEndOfWord = true;
    node.value = word;
  }

  /**
   * Finds the longest prefix match for the given text.
   * Returns the longest stored word that is a prefix of the input text.
   *
   * @param text - The input string to find prefix matches for
   * @returns Object containing the longest matching prefix and remaining text
   */
  findLongestPrefix(text: string): { match: string; remaining: string } {
    let current = this.root;
    let longestMatch = { match: "", remaining: text };

    // Traverse the trie character by character
    for (let i = 0; i < text.length; i++) {
      const char = text[i];

      // Stop if no path exists for this character
      if (!current.children.has(char)) {
        break;
      }

      // Move to the next nodes
      current = current.children.get(char)!;

      // Update longest match if we've reached a complete word
      if (current.isEndOfWord) {
        longestMatch = {
          match: current.value,
          remaining: text.slice(i + 1),
        };
      }
    }

    return longestMatch;
  }
}
