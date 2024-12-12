class RadixSorter:
    def __init__(self):
        self.mIndices = None
        self.mIndices2 = None
        self.mCurrentSize = 0

        # Allocate input-independent ram
        self.mHistogram = [0] * (256 * 4)
        self.mOffset = [0] * 256

        # Initialize indices
        self.reset_indices()

    def get_indicies(self):
        return self.mIndices

    def __del__(self):
        # Release everything
        del self.mOffset
        del self.mHistogram
        del self.mIndices2
        del self.mIndices

    def sort(self, input, nb, signedvalues=True):
        # Resize lists if needed
        if nb > self.mCurrentSize:
            # Free previously used ram
            del self.mIndices2
            del self.mIndices

            # Get some fresh one
            self.mIndices = [0] * nb
            self.mIndices2 = [0] * nb
            self.mCurrentSize = nb

            # Initialize indices so that the input buffer is read in sequential order
            self.reset_indices()

        # Clear counters
        self.mHistogram = [0] * (256 * 4)

        # Create histograms (counters). Counters for all passes are created in one run.
        # Pros: read input buffer once instead of four times
        # Cons: mHistogram is 4Kb instead of 1Kb
        # We must take care of signed/unsigned values for temporal coherence.... I just
        # have 2 code paths even if just a single opcode changes. Self-modifying code, someone?

        # Temporal coherence
        AlreadySorted = True  # Optimism...
        Indices = self.mIndices
        # Prepare to count
        p = input
        pe = nb * 4
        h0 = self.mHistogram[0:256]  # Histogram for first pass (LSB)
        h1 = self.mHistogram[256:512]  # Histogram for second pass
        h2 = self.mHistogram[512:768]  # Histogram for third pass
        h3 = self.mHistogram[768:1024]  # Histogram for last pass (MSB)
        if not signedvalues:
            # Temporal coherence
            PrevVal = input[self.mIndices[0]]

            for i in range(pe):
                # Temporal coherence
                Val = input[Indices[i]]  # Read input buffer in previous sorted order
                if Val < PrevVal:
                    AlreadySorted = False  # Check whether already sorted or not
                PrevVal = Val  # Update for next iteration

                # Create histograms
                h0[p[i]] += 1
                h1[p[i]] += 1
                h2[p[i]] += 1
                h3[p[i]] += 1
        else:
            # Temporal coherence
            PrevVal = input[self.mIndices[0]]

            for i in range(pe):
                # Temporal coherence
                Val = input[Indices[i]]  # Read input buffer in previous sorted order
                if Val < PrevVal:
                    AlreadySorted = False  # Check whether already sorted or not
                PrevVal = Val  # Update for next iteration

                # Create histograms
                h0[p[i]] += 1
                h1[p[i]] += 1
                h2[p[i]] += 1
                h3[p[i]] += 1

        # If all input values are already sorted, we just have to return and leave the previous list unchanged.
        # That way the routine may take advantage of temporal coherence, for example when used to sort transparent faces.
        if AlreadySorted:
            return self

        # Compute #negative values involved if needed
        NbNegativeValues = 0
        if signedvalues:
            # An efficient way to compute the number of negatives values we'll have to deal with is simply to sum the 128
            # last values of the last histogram. Last histogram because that's the one for the Most Significant Byte,
            # responsible for the sign. 128 last values because the 128 first ones are related to positive numbers.
            h3 = self.mHistogram[768:1024]
            for i in range(128, 256):
                NbNegativeValues += h3[i]  # 768 for last histogram, 128 for negative part

        # Radix sort, j is the pass number (0=LSB, 3=MSB)
        for j in range(4):
            # Shortcut to current counters
            CurCount = self.mHistogram[j << 8:(j + 1) << 8]

            # Reset flag. The sorting pass is supposed to be performed. (default)
            PerformPass = True

            # Check pass validity [some cycles are lost there in the generic case, but that's ok, just a little loop]
            for i in range(256):
                # If all values have the same byte, sorting is useless. It may happen when sorting bytes or words instead of dwords.
                # This routine actually sorts words faster than dwords, and bytes faster than words. Standard running time (O(4*n))is
                # reduced to O(2*n) for words and O(n) for bytes. Running time for floats depends on actual values...
                if CurCount[i] == nb:
                    PerformPass = False
                    break
                # If at least one count is not null, we suppose the pass must be done. Hence, this test takes very few CPU time in the generic case.
                if CurCount[i]:
                    break

            # Sometimes the fourth (negative) pass is skipped because all numbers are negative and the MSB is 0xFF (for example). This is
            # not a problem, numbers are correctly sorted anyway.
            if PerformPass:
                # Should we care about negative values?
                if j != 3 or not signedvalues:
                    # Here we deal with positive values only

                    # Create offsets
                    self.mOffset[0] = 0
                    for i in range(1, 256):
                        self.mOffset[i] = self.mOffset[i - 1] + CurCount[i - 1]
                else:
                    # This is a special case to correctly handle negative integers. They're sorted in the right order but at the wrong place.

                    # Create biased offsets, in order for negative numbers to be sorted as well
                    self.mOffset[0] = NbNegativeValues  # First positive number takes place after the negative ones
                    for i in range(1, 128):
                        self.mOffset[i] = self.mOffset[i - 1] + CurCount[i - 1]  # 1 to 128 for positive numbers

                    # Fixing the wrong place for negative values
                    self.mOffset[128] = 0
                    for i in range(129, 256):
                        self.mOffset[i] = self.mOffset[i - 1] + CurCount[i - 1]

                # Perform Radix Sort
                InputBytes = input
                Indices = self.mIndices
                IndicesEnd = nb
                InputBytes = [InputBytes[i] >> (j * 8) & 0xFF for i in range(len(InputBytes))]
                for i in range(IndicesEnd):
                    id = Indices[i]
                    self.mIndices2[self.mOffset[InputBytes[id]]] += 1

                # Swap pointers for next pass
                Tmp = self.mIndices
                self.mIndices = self.mIndices2
                self.mIndices2 = Tmp

        return self

    def reset_indices(self):
        self.mIndices = [i for i in range(self.mCurrentSize)]
        return self

    def get_used_ram(self):
        UsedRam = 0
        UsedRam += 256 * 4 * 4  # Histograms
        UsedRam += 256 * 4  # Offsets
        UsedRam += 2 * self.mCurrentSize * 4  # 2 lists of indices
        return UsedRam
