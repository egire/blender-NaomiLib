class CustomArray:
    def __init__(self, startsize=0, inputbuffer=None):
        self.data = []
        self.collapsed = None

    def Store(self, value):
        self.data.append(value)
        return self

    def Collapse(self):
        self.collapsed = self.data
        return self.collapsed

    def __del__(self):
        del self.data


class Adjacencies:
    def __init__(self):
        self.mNbFaces = 0
        self.mFaces = []

    def Init(self, create):
        self.mNbFaces = create.NbFaces
        self.mFaces = [AdjTriangle() for _ in range(self.mNbFaces)]
        return True

    def CreateDatabase(self):
        return True


class AdjTriangle:
    def __init__(self):
        self.VRef = [0, 0, 0]
        self.ATri = [0, 0, 0]

    def OppositeVertex(self, vref0, vref1):
        for v in self.VRef:
            if v != vref0 and v != vref1:
                return v
        return None

    def FindEdge(self, vref0, vref1):
        for i, (v0, v1) in enumerate(zip(self.VRef, self.VRef[1:] + self.VRef[:1])):
            if (v0 == vref0 and v1 == vref1) or (v0 == vref1 and v1 == vref0):
                return i
        return None


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

    def Init(self, create):
        self.FreeUsedRam()
        self.mAdj = Adjacencies()
        if not self.mAdj.Init(create):
            return False
        if not self.mAdj.CreateDatabase():
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
        Strip = [None] * 3
        Faces = [None] * 3
        Length = [0] * 3
        FirstLength = [0] * 3

        Refs0 = [self.mAdj.mFaces[face].VRef[0], self.mAdj.mFaces[face].VRef[2], self.mAdj.mFaces[face].VRef[1]]
        Refs1 = [self.mAdj.mFaces[face].VRef[1], self.mAdj.mFaces[face].VRef[0], self.mAdj.mFaces[face].VRef[2]]

        for j in range(3):
            Strip[j] = [0xFFFFFFFF] * (self.mAdj.mNbFaces + 2 + 1 + 2)
            Faces[j] = [0xFFFFFFFF] * (self.mAdj.mNbFaces + 2)
            Tags = self.mTags[:]
            Length[j] = self.TrackStrip(face, Refs0[j], Refs1[j], Strip[j], Faces[j], Tags)
            FirstLength[j] = Length[j]

            Strip[j][:Length[j]] = reversed(Strip[j][:Length[j]])
            Faces[j][:Length[j] - 2] = reversed(Faces[j][:Length[j] - 2])

            NewRef0 = Strip[j][Length[j] - 3]
            NewRef1 = Strip[j][Length[j] - 2]
            ExtraLength = self.TrackStrip(face, NewRef0, NewRef1, Strip[j][Length[j] - 3:], Faces[j][Length[j] - 3:], Tags)
            Length[j] += ExtraLength - 3

        Longest = max(Length)
        Best = Length.index(Longest)
        NbFaces = Longest - 2

        for j in range(Longest - 2):
            self.mTags[Faces[Best][j]] = True

        if self.mOneSided and FirstLength[Best] & 1:
            if Longest == 3 or Longest == 4:
                Strip[Best][1], Strip[Best][2] = Strip[Best][2], Strip[Best][1]
            else:
                Strip[Best][:Longest] = reversed(Strip[Best][:Longest])
                NewPos = Longest - FirstLength[Best]
                if not NewPos & 1:
                    Strip[Best].insert(0, Strip[Best][0])
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
        Length = 2
        strip[0] = oldest
        strip[1] = middle

        DoTheStrip = True
        while DoTheStrip:
            Newest = self.mAdj.mFaces[face].OppositeVertex(oldest, middle)
            strip[Length] = Newest
            Length += 1
            faces.append(face)
            tags[face] = True

            CurEdge = self.mAdj.mFaces[face].FindEdge(middle, Newest)
            Link = self.mAdj.mFaces[face].ATri[CurEdge]
            if self.IS_BOUNDARY(Link):
                DoTheStrip = False
            else:
                face = self.MAKE_ADJ_TRI(Link)
                if tags[face]:
                    DoTheStrip = False
            oldest = middle
            middle = Newest
        return Length

    def ConnectAllStrips(self, result):
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
        return link == 0xFFFFFFFF

    def MAKE_ADJ_TRI(self, link):
        return link & 0x3FFFFFFF


class StriperCreate:
    def __init__(self):
        self.NbFaces = 0
        self.DFaces = None
        self.WFaces = None
        self.AskForWords = False
        self.OneSided = False
        self.SGIAlgorithm = False
        self.ConnectAllStrips = False


class StriperResult:
    def __init__(self):
        self.NbStrips = 0
        self.StripLengths = None
        self.StripRuns = None
        self.AskForWords = False
