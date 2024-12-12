class EHeapPair:
    def __init__(self, data, key, pos):
        self.data = data
        self.key = key
        self.pos = pos

class EHeap:
    def __init__(self, key_func=None, data=None):
        self.elts = []
        self.func = key_func
        self.data = data
        self.frozen = False
        self.randomized = False

    def __len__(self):
            return len(self.elts)

    def sift_up(self, i):
        child = self.elts[i - 1]
        key = child.key
        while (p := (i // 2) if i >= 2 else 0):
            parent = self.elts[p - 1]
            if parent.key > key or (self.randomized and parent.key == key and random.random() < 0.5):
                self.elts[p - 1], self.elts[i - 1] = child, parent
                child.pos, parent.pos = p, i
                i = p
            else:
                break

    def insert(self, p):
        if not self.func:
            return None
        pair = EHeapPair(p, self.func(p, self.data), len(self.elts) + 1)
        self.elts.append(pair)
        if not self.frozen:
            self.sift_up(len(self.elts))
        return pair

    def insert_with_key(self, p, key):
        pair = EHeapPair(p, key, len(self.elts) + 1)
        self.elts.append(pair)
        if not self.frozen:
            self.sift_up(len(self.elts))
        return pair

    def sift_down(self, i):
        parent = self.elts[i - 1]
        key = parent.key
        while (lc := 2 * i) <= len(self.elts):
            rc = lc + 1
            left_child = self.elts[lc - 1]
            right_child = self.elts[rc - 1] if rc <= len(self.elts) else None
            if not right_child or left_child.key < right_child.key:
                child, c = left_child, lc
            else:
                child, c = right_child, rc
            if key > child.key:
                self.elts[i - 1], self.elts[c - 1] = child, parent
                child.pos, parent.pos = i, c
                i = c
            else:
                break

    def remove_top(self, key=None):
        if not self.elts:
            return None
        if len(self.elts) == 1:
            pair = self.elts.pop(0)
            if key is not None:
                key = pair.key
            return pair.data
        pair = self.elts[0]
        root = pair.data
        if key is not None:
            key = pair.key
        self.elts[0] = self.elts.pop()
        self.elts[0].pos = 1
        self.sift_down(1)
        return root

    def top(self, key=None):
        if not self.elts:
            return None
        pair = self.elts[0]
        if key is not None:
            key = pair.key
        return pair.data

    def destroy(self):
        self.elts.clear()

    def thaw(self):
        if not self.frozen:
            return
        for i in range(len(self.elts) // 2, 0, -1):
            self.sift_down(i)
        self.frozen = False

    def foreach(self, func, data):
        for pair in self.elts:
            func(pair.data, data)

    def remove(self, p):
        i = p.pos
        data = p.data
        while (par := (i // 2) if i >= 2 else 0):
            parent = self.elts[par - 1]
            self.elts[par - 1], self.elts[i - 1] = p, parent
            p.pos, parent.pos = par, i
            i = par
        self.remove_top()
        return data

    def decrease_key(self, p, new_key):
        i = p.pos
        if new_key > p.key:
            return
        p.key = new_key
        if not self.frozen:
            self.sift_up(i)

    def freeze(self):
        self.frozen = True

    def size(self):
        return len(self.elts)

    def update(self):
        if not self.func:
            return
        self.frozen = True
        for pair in self.elts:
            pair.key = self.func(pair.data, self.data)
        self.thaw()

    def key(self, p):
        if not self.func:
            return 0.0
        return self.func(p, self.data)

    def set_randomized(self, randomized):
        self.randomized = randomized
