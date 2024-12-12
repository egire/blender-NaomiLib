import numpy as np

from RevisitedRadix import RadixSorter

sbyte = np.int8
ubyte = np.uint8
sword = np.int16
uword = np.uint16
sdword = np.int32
udword = np.uint32
sqword = np.int64
uqword = np.uint64
sfloat = np.float32


class AdjTriangle:
    def __init__(self):
        self.VRef = [udword()] * 3
        self.ATri = [udword()] * 3

    def find_edge(self, vref0, vref1):
        EdgeNb = ubyte(0xff);

        if (self.VRef[0] == vref0 and self.VRef[1] == vref1) or (self.VRef[0] == vref1 and self.VRef[1] == vref0):
            return 0
        if (self.VRef[0] == vref0 and self.VRef[2] == vref1) or (self.VRef[0] == vref1 and self.VRef[2] == vref0):
            return 1
        if (self.VRef[1] == vref0 and self.VRef[2] == vref1) or (self.VRef[1] == vref1 and self.VRef[2] == vref0):
            return 2
        return EdgeNb

    def opposite_vertex(self, vref0, vref1):
        Ref = udword(0xffffffff)

        if (self.VRef[0] == vref0 and self.VRef[1] == vref1) or (self.VRef[0] == vref1 and self.VRef[1] == vref0):
            return self.VRef[2]
        if (self.VRef[0] == vref0 and self.VRef[2] == vref1) or (self.VRef[0] == vref1 and self.VRef[2] == vref0):
            return self.VRef[1]
        if (self.VRef[1] == vref0 and self.VRef[2] == vref1) or (self.VRef[1] == vref1 and self.VRef[2] == vref0):
            return self.VRef[0]
        return Ref


class AdjEdge:
    def __init__(self, ref0 = 0, ref1 = 0, face_nb = 0):
        self.Ref0 = udword(ref0)
        self.Ref1 = udword(ref1)
        self.FaceNb = udword(face_nb)


class AdjacenciesCreate:
    def __init__(self):
        self.NbFaces = 0
        self.DFaces = None
        self.WFaces = None


class Adjacencies:
    def __init__(self):
        self.mNbEdges = 0
        self.mCurrentNbFaces = 0
        self.mEdges = None
        self.mNbFaces = 0
        self.mFaces = None

    def __del__(self):
        self.mEdges = None
        self.mFaces = None

    def init(self, create: AdjacenciesCreate):
        self.mNbFaces = create.NbFaces
        self.mFaces = [AdjTriangle() for _ in range(self.mNbFaces)]
        if not self.mFaces:
            return False
        self.mEdges = [AdjEdge() for _ in range(self.mNbFaces * 3)]
        if not self.mEdges:
            return False

        for i in range(self.mNbFaces):
            ref0 = create.DFaces[i * 3 + 0] if create.DFaces else create.WFaces[i * 3 + 0] if create.WFaces else 0
            ref1 = create.DFaces[i * 3 + 1] if create.DFaces else create.WFaces[i * 3 + 1] if create.WFaces else 1
            ref2 = create.DFaces[i * 3 + 2] if create.DFaces else create.WFaces[i * 3 + 2] if create.WFaces else 2
            self.add_triangle(ref0, ref1, ref2)

        return True

    def add_triangle(self, ref0, ref1, ref2):
        self.mFaces[self.mCurrentNbFaces].VRef[0] = udword(ref0)
        self.mFaces[self.mCurrentNbFaces].VRef[1] = udword(ref1)
        self.mFaces[self.mCurrentNbFaces].VRef[2] = udword(ref2)
        self.mFaces[self.mCurrentNbFaces].ATri[0] = udword(-1)
        self.mFaces[self.mCurrentNbFaces].ATri[1] = udword(-1)
        self.mFaces[self.mCurrentNbFaces].ATri[2] = udword(-1)

        if ref0 < ref1:
            self.add_edge(ref0, ref1, self.mCurrentNbFaces)
        else:
            self.add_edge(ref1, ref0, self.mCurrentNbFaces)
        if ref0 < ref2:
            self.add_edge(ref0, ref2, self.mCurrentNbFaces)
        else:
            self.add_edge(ref2, ref0, self.mCurrentNbFaces)
        if ref1 < ref2:
            self.add_edge(ref1, ref2, self.mCurrentNbFaces)
        else:
            self.add_edge(ref2, ref1, self.mCurrentNbFaces)

        self.mCurrentNbFaces += 1
        return True

    def add_edge(self, ref0, ref1, face):
        self.mEdges[self.mNbEdges].Ref0 = ref0
        self.mEdges[self.mNbEdges].Ref1 = ref1
        self.mEdges[self.mNbEdges].FaceNb = face
        self.mNbEdges += 1
        return True

    def create_database(self):
        core = RadixSorter()
        face_nb = [self.mEdges[i].FaceNb for i in range(self.mNbEdges)]
        vrefs0 = [self.mEdges[i].Ref0 for i in range(self.mNbEdges)]
        vrefs1 = [self.mEdges[i].Ref1 for i in range(self.mNbEdges)]

        sorted_indices = core.sort(face_nb, self.mNbEdges).sort(vrefs0, self.mNbEdges).sort(vrefs0, self.mNbEdges).get_indicies()

        last_ref0 = vrefs0[sorted_indices[0]]
        last_ref1 = vrefs1[sorted_indices[0]]
        count = 0
        tmp_buffer = [0, 0, 0]

        for i in range(self.mNbEdges):
            face = face_nb[sorted_indices[i]]
            ref0 = vrefs0[sorted_indices[i]]
            ref1 = vrefs1[sorted_indices[i]]
            if ref0 == last_ref0 and ref1 == last_ref1:
                tmp_buffer[count] = face
                count += 1
                if count == 3:
                    return False
            else:
                if count == 2:
                    status = self.update_link(tmp_buffer[0], tmp_buffer[1], last_ref0, last_ref1)
                    if not status:
                        return status
                count = 0
                tmp_buffer[count] = face
                count += 1
                last_ref0 = ref0
                last_ref1 = ref1

        status = True
        if count == 2:
            status = self.update_link(tmp_buffer[0], tmp_buffer[1], last_ref0, last_ref1)

        self.mEdges = None
        return status

    def update_link(self, firsttri, secondtri, ref0, ref1):
        tri0 = self.mFaces[firsttri]
        tri1 = self.mFaces[secondtri]

        edge_nb0 = tri0.find_edge(ref0, ref1)
        if edge_nb0 == 0xff:
            return False
        edge_nb1 = tri1.find_edge(ref0, ref1)
        if edge_nb1 == 0xff:
            return False

        tri0.ATri[edge_nb0] = secondtri | (edge_nb1 << 30)
        tri1.ATri[edge_nb1] = firsttri | (edge_nb0 << 30)
        return True