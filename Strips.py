from Striper import Striper, StriperCreate, StriperResult

def main():
    Topology = [
        0, 1, 2,
        1, 2, 3,
        2, 3, 4,
        3, 4, 5,
        4, 5, 6,
        5, 6, 7,
        6, 7, 8,
        7, 8, 9
    ]

    sc = StriperCreate()
    sc.DFaces = Topology
    sc.NbFaces = 8
    sc.AskForWords = True
    sc.ConnectAllStrips = False
    sc.OneSided = False
    sc.SGIAlgorithm = True

    Strip = Striper()
    Strip.Init(sc)

    sr = StriperResult()
    sr.StripRuns = Topology
    Strip.Compute(sr)

    print(f"Number of strips: {sr.NbStrips}")
    Refs = sr.StripRuns
    for i in range(sr.NbStrips):
        print(f"Strip {i}:   ", end="")
        NbRefs = sr.StripLengths[i]
        for j in range(NbRefs):
            print(f"{Refs[j]} ", end="")
        print()

if __name__ == "__main__":
    main()
