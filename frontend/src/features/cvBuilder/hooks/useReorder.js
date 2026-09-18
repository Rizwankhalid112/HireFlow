import { useCallback } from 'react';

/*
 * Moves one item within a list and sends the whole ordered id array.
 * The backend reorder endpoint rejects the entire batch if any id fails the
 * ownership check, so a partial array must never be sent.
 */
export function useReorder(items, reorderMutation, buildArgs) {
  const { mutate, isPending } = reorderMutation;

  const move = useCallback(
    (index, direction) => {
      const target = index + direction;
      if (index < 0 || target < 0 || target >= items.length) {
        return;
      }

      const next = [...items];
      [next[index], next[target]] = [next[target], next[index]];
      const orderedIds = next.map((item) => item.id);

      mutate(buildArgs ? buildArgs(orderedIds) : orderedIds);
    },
    [items, mutate, buildArgs],
  );

  return {
    moveUp: (index) => move(index, -1),
    moveDown: (index) => move(index, 1),
    isReordering: isPending,
  };
}
