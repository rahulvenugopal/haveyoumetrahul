# Do HRV right


1. [ECG Time Series Variability Analysis Engineering and Medicine](https://www.routledge.com/ECG-Time-Series-Variability-Analysis-Engineering-and-Medicine/Jelinek-Cornforth-Khandoker/p/book/9780367870157#) by Cornforth, David Jelinek, Herbert Franz Khandoker, Ahsan Habib, 2018
2. [Considerations in the assessment of heart rate variability in biobehavioral research](https://pubmed.ncbi.nlm.nih.gov/25101047/)
3. [Simple HRV analysis pipeline and documentation from Neurokit2](https://github.com/rahulvenugopal/HRV_adventures)
> Water intake increases HRV in a dose dependent manner [Water consumption as a source of error in the measurement of heart rate variability](https://osf.io/83exy/)
> Caffeine intake, some medications, alcohol consumption, time of day, exercise, food inatake, water intake and bladder filling influence HRV
4. [Statistical considerations for reporting and planning heart rate variability case-control studies](https://pubmed.ncbi.nlm.nih.gov/27914167/)
5. [Guidelines for Reporting Articles on Psychiatry and Heart rate variability (GRAPH): recommendations to advance research communication](https://www.nature.com/articles/tp201673)

{{% admonition type="note" title="Note" %}}
So, I collected ECG data using lead I and Neurokit2 failed to pickup the R peaks correctly and ended up picking up S! Deep diving to know why
{{% /admonition %}}

Let us look at what happens to the ECG data once it enters the pipeline.

#### Stop 1: `ecg_clean`
- Default method to clean ECG is `neurokit`
- Check for any `nan` in the data and returns missing datapoints
- If there are gaps, they are filled with last available value (forward filling method)
- There is a high pass filter set at `0.5` Hz butterworth filter (order = 5), followed by a powerline filtering (By default, `powerline = 50`)

#### Stop 2: `ecg_peaks`
- Default method to identify peaks is `neurokit`
- QRS complexes are detected based on the steepness of the absolute gradient of the ECG signal. Subsequently, R-peaks are detected as local maxima in the QRS complexes. Refer this [paper](https://joss.theoj.org/papers/10.21105/joss.02621) for details

#### In short
1. Compute the ECG gradient to detect rapid changes in slope (rate of change)
{{< figure src="1 Raw data.png">}}
{{< figure src="2 Gradient.png">}}
Take absolute values of gradient so that we don't miss out negative going waves
{{< figure src="3 Abs Gradient.png">}}
2. Smooth the absolute gradient to reduce noise using one tenth of a second long `boxcar` kernel
{{< figure src="4 Smooth grad.png">}}
One more level of smoothing using 75 percent of a second long kernel. This would be ultra smooth
{{< figure src="5 avggrad.png">}}
3.Set a dynamic threshold to identify QRS complexes using the double smooth signal. The threshold is set at 1.5 times the smooth curve optimised for finding peaks
{{< figure src="6 DynamicThreshold.png">}}
4. Detect QRS start and end points based on threshold crossing
{{< figure src="8 Start and End of QRS Detection.png">}}
5. Filter out short QRS complexes that are likely noise
The values are set at one third of a second
6. Find the most prominent peak within each QRS complex. **This happens via the** `locmax[np.argmax(props["prominences"])]`. `locmax` **sees only peaks and not troughs**
{{< figure src="9 QRS Complex.png">}}
> This is really critical for R peak detection. If our ECG waveform is flipped (R peaks pointing down), the algorithm would pick the S peak (falling end of R) instead of the peak! See the final comparisons
7. Apply a refractory period to prevent false detections. Once a peak is detected for identified `QRS` complex, it compares its proximity to previously identified peak of previous `QRS` complex. If it is within one third of a second, the current peak is dropped. More like a refractory period idea implemeneted
8. See the identified peaks
{{< figure src="10 Overlay identified R peak.png">}}

### See what happens when we flip the ECG waveform
R peaks pointing up
{{< figure src="Positive.png">}}
R peaks pointing down
{{< figure src="Negative.png">}}

> Observations
- The delay in R peak (time from R peak to S peak)
- The whole interval gets shifted
- The numbers above red dots in panel 1 are the locations of R peak detections
- The algorithm becomes an S peak detector
- Should we be worries? YES offcourse
- The RR interval remains more or less similar in both the scenarios

**Positive:** 664, 680, 723, 732, 711, 707, 737, 738, 734, 713, 726, 752, 718

**Negative:** 664, 680, 722, 732, 712, 706, 737, 738, 734, 713, 726, 752, 719
