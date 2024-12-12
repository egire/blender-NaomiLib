
from Adjacency import Adjacencies, AdjacenciesCreate

from CustomArray import CustomArray

import numpy as np

sbyte = np.int8
ubyte = np.uint8
sword = np.int16
uword = np.uint16
sdword = np.int32
udword = np.uint32
sqword = np.int64
uqword = np.uint64
sfloat = np.float32

class StriperResult:
    def __init__(self):
        self.NbStrips = 0
        self.StripLengths = None
        self.StripRuns = None
        self.AskForWords = False

class StriperCreate:
    def __init__(self):
        self.NbFaces = 0
        self.DFaces = None
        self.WFaces = None
        self.AskForWords = False
        self.OneSided = False
        self.SGIAlgorithm = False
        self.ConnectAllStrips = False

class Striper:
    def __init__(self):
        self.mAdj = None
        self.mTags = None
        self.mStripLengths = None
        self.mStripRuns = None
        self.mSingleStrip = None

    def __del__(self):
        self.FreeUsedRam()

    def FreeUsedRam(self):
        self.mSingleStrip = None
        self.mStripRuns = None
        self.mStripLengths = None
        self.mTags = None
        self.mAdj = None
        return self

    def Init(self, create: StriperCreate):
        self.FreeUsedRam()
        self.mAdj = Adjacencies()
        adjCreate = AdjacenciesCreate()

        adjCreate.NbFaces = create.NbFaces
        adjCreate.DFaces = create.DFaces
        adjCreate.WFaces = create.WFaces

        if not self.mAdj.init(adjCreate):
            return False
        if not self.mAdj.create_database():
            return False
        self.mAskForWords = create.AskForWords
        self.mOneSided = create.OneSided
        self.mSGIAlgorithm = create.SGIAlgorithm
        self.mConnectAllStrips = create.ConnectAllStrips
        return True

    def Compute(self, result):
        if not self.mAdj:
            return False

        self.mStripLengths = CustomArray()
        self.mStripRuns = CustomArray()
        self.mTags = [False] * self.mAdj.mNbFaces
        Connectivity = [0] * self.mAdj.mNbFaces

        if self.mSGIAlgorithm:
            for i in range(self.mAdj.mNbFaces):
                Tri = self.mAdj.mFaces[i]
                if not self.IS_BOUNDARY(Tri.ATri[0]):
                    Connectivity[i] += 1
                if not self.IS_BOUNDARY(Tri.ATri[1]):
                    Connectivity[i] += 1
                if not self.IS_BOUNDARY(Tri.ATri[2]):
                    Connectivity[i] += 1

            Sorted = sorted(range(len(Connectivity)), key=lambda k: Connectivity[k])
            Connectivity = Sorted
        else:
            for i in range(self.mAdj.mNbFaces):
                Connectivity[i] = i

        self.mNbStrips = 0
        TotalNbFaces = 0
        Index = 0

        while TotalNbFaces != self.mAdj.mNbFaces:
            while self.mTags[Connectivity[Index]]:
                Index += 1
            FirstFace = Connectivity[Index]
            TotalNbFaces += self.ComputeBestStrip(FirstFace)
            self.mNbStrips += 1

        result.NbStrips = self.mNbStrips
        result.StripLengths = self.mStripLengths.Collapse()
        result.StripRuns = self.mStripRuns.Collapse()

        if self.mConnectAllStrips:
            self.ConnectAllStrips(result)

        return True

    def ComputeBestStrip(self, face):
        Strip = [None] * 3  # Strips computed in the 3 possible directions
        Faces = [None] * 3  # Faces involved in the 3 previous strips
        Length = [0] * 3  # Lengths of the 3 previous strips

        FirstLength = [0] * 3  # Lengths of the first parts of the strips are saved for culling

        Refs0 = [udword()] * 3
        Refs1 = [udword()] * 3

        Refs0[0] = self.mAdj.mFaces[face].VRef[0]
        Refs1[0] = self.mAdj.mFaces[face].VRef[1]

	    # Bugfix  self.y Er. Malafeew!
        Refs0[1] = self.mAdj.mFaces[face].VRef[2]
        Refs1[1] = self.mAdj.mFaces[face].VRef[0]

        Refs0[2] = self.mAdj.mFaces[face].VRef[1]
        Refs1[2] = self.mAdj.mFaces[face].VRef[2]

        for j in range(3):
            Strip[j] = np.full((self.mAdj.mNbFaces + 2 + 1 + 2), 0xff, dtype=udword)
            Faces[j] = np.full((self.mAdj.mNbFaces + 2), 0xff, dtype=udword)

            Tags = self.mTags.copy()

            Length[j] = self.TrackStrip(face, Refs0[j], Refs1[j], Strip[j], Faces[j], Tags)
            FirstLength[j] = Length[j]

            for i in range(Length[j] // 2):
                Strip[j][i], Strip[j][Length[j] - i - 1] = Strip[j][Length[j] - i - 1], Strip[j][i]

            for i in range((Length[j] - 2) // 2):
                Faces[j][i], Faces[j][Length[j] - i - 3] = Faces[j][Length[j] - i - 3], Faces[j][i]

            NewRef0 = udword(Strip[j][Length[j] - 3])
            NewRef1 = udword(Strip[j][Length[j] - 2])

            ExtraLength = self.TrackStrip(face, NewRef0, NewRef1, Strip[j][Length[j] - 3:], Faces[j][Length[j] - 3:], Tags)
            Length[j] += ExtraLength - 3


        Longest = Length[0]
        Best = 0
        if Length[1] > Longest:
            Longest = Length[1]
            Best = 1
        if Length[2] > Longest:
            Longest = Length[2]
            Best = 2

        NbFaces = Longest - 2

        for j in range(Longest - 2):
            self.mTags[Faces[Best][j]] = True

        if self.mOneSided and FirstLength[Best] & 1:
            if Longest == 3 or Longest == 4:
                Strip[Best][1], Strip[Best][2] = Strip[Best][2], Strip[Best][1]
            else:
                # "to reverse the strip, write it in reverse order"
                for j in range(Longest // 2):
                    Strip[Best][j], Strip[Best][Longest - j - 1] = Strip[Best][Longest - j - 1], Strip[Best][j]

                # "If the position of the original face in this new reversed strip is odd, you're done"
                NewPos = Longest - FirstLength[Best]
                if NewPos & 1:
                    # "Else replicate the first index"
                    for j in range(Longest, 0, -1):
                        Strip[Best][j] = Strip[Best][j - 1]
                    Longest += 1

        for j in range(Longest):
            Ref = Strip[Best][j]
            if self.mAskForWords:
                self.mStripRuns.Store(int(Ref))
            else:
                self.mStripRuns.Store(Ref)
        self.mStripLengths.Store(Longest)

        return NbFaces

    def TrackStrip(self, face, oldest, middle, strip, faces, tags):
        Length = 2  # Initial length is 2 since we have 2 indices in input
        strip[0] = oldest  # First index of the strip
        strip[1] = middle  # Second index of the strip

        DoTheStrip = True
        while DoTheStrip:
            Newest = self.mAdj.mFaces[face].opposite_vertex(oldest, middle)  # Get the third index of a face given two of them
            np.append(strip, Newest)  # Extend the strip,...
            np.append(faces, face)  # ...keep track of the face,...
            tags[face] = True  # ...and mark it as "done".

            CurEdge = self.mAdj.mFaces[face].find_edge(middle, Newest)  # Get the edge ID...

            Link = self.mAdj.mFaces[face].ATri[CurEdge]  # ...and use it to catch the link to adjacent face.
            if self.IS_BOUNDARY(Link):
                DoTheStrip = False  # If the face is no more connected, we're done...
            else:
                face = self.MAKE_ADJ_TRI(Link)  # ...else the link gives us the new face index.
                if tags[face]:
                    DoTheStrip = False  # Is the new face already done?
            oldest = middle  # Shift the indices and wrap
            middle = Newest

        return Length


    def ConnectAllStrips(self, result: StriperResult):
        self.mSingleStrip = CustomArray()
        if not self.mSingleStrip:
            return False

        self.mTotalLength = 0
        wrefs = result.StripRuns if result.AskForWords else None
        drefs = None if result.AskForWords else result.StripRuns

        for k in range(result.NbStrips):
            if k:
                LastRef = drefs[-1] if drefs else int(wrefs[-1])
                FirstRef = drefs[0] if drefs else int(wrefs[0])
                if self.mAskForWords:
                    self.mSingleStrip.Store(int(LastRef)).Store(int(FirstRef))
                else:
                    self.mSingleStrip.Store(LastRef).Store(FirstRef)
                self.mTotalLength += 2

                if self.mOneSided:
                    if self.mTotalLength & 1:
                        SecondRef = drefs[1] if drefs else int(wrefs[1])
                        if FirstRef != SecondRef:
                            if self.mAskForWords:
                                self.mSingleStrip.Store(int(FirstRef))
                            else:
                                self.mSingleStrip.Store(FirstRef)
                            self.mTotalLength += 1
                        else:
                            result.StripLengths[k] -= 1
                            if wrefs:
                                wrefs = wrefs[1:]
                            if drefs:
                                drefs = drefs[1:]

            for j in range(result.StripLengths[k]):
                Ref = drefs[j] if drefs else int(wrefs[j])
                if self.mAskForWords:
                    self.mSingleStrip.Store(int(Ref))
                else:
                    self.mSingleStrip.Store(Ref)
            if wrefs:
                wrefs = wrefs[result.StripLengths[k]:]
            if drefs:
                drefs = drefs[result.StripLengths[k]:]
            self.mTotalLength += result.StripLengths[k]

        result.NbStrips = 1
        result.StripRuns = self.mSingleStrip.Collapse()
        result.StripLengths = [self.mTotalLength]

        return True

    def IS_BOUNDARY(self, link):
        return link == np.uint32(0xFFFFFFFF)

    def MAKE_ADJ_TRI(self, link):
        return link & np.uint32(0x3FFFFFFF)

    def GET_EDGE_NB(x):
        return x >> 30