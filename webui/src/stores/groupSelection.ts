import { writable } from 'svelte/store';

type GroupSelectionStore = {
    selectedGroupId: number | null;
};

function createGroupSelection() {
    const { subscribe, set, update } = writable<GroupSelectionStore>({
        selectedGroupId: null
    });

    return {
        subscribe,
        set: (groupId: number | null) => {
            set({ selectedGroupId: groupId });
        },
        reset: () => set({ selectedGroupId: null })
    };
}

export const groupSelection = createGroupSelection();
