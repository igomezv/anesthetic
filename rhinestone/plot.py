""" Main plotting tools."""
import numpy
import matplotlib.pyplot as plt
from matplotlib.gridspec import (GridSpec as GS,
                                 GridSpecFromSubplotSpec as sGS)
from rhinestone.widgets import (Widget, Slider, Button,
                                RadioButtons, TrianglePlot, CheckButtons)
from anesthetic.anesthetic import NestedSamples


class Higson(Widget):
    """ Higson plot as shown in https://arxiv.org/abs/1703.09701 .

    Attributes:
        curve (matplotlib.lines.Line2D):
            points currently plotted as a curve.

        point (matplotlib.lines.Line2D):
            large indicator point currently plotted on the curve.
    """
    def __init__(self, fig, gridspec):
        super(Higson, self).__init__(fig, gridspec)
        self.ax.set_yticks([])
        self.ax.set_ylim(-0.1, 1.1)
        self.ax.set_ylabel(r'$LX$')
        self.ax.set_xlabel(r'$\log X$')

        self.curve, = self.ax.plot([None], [None], 'k-')
        self.point, = self.ax.plot([None], [None], 'ko')

    def update(self, logX, LX, i):
        """ Update the line and the point in the higson plot.

        Args:
            logX (array):
                log-volume compression values to plot

            LX (array):
                Likelihood * volume compression

            i (int):
                Current location of higson point
        """
        self.point.set_xdata(logX[i])
        self.point.set_ydata(LX[i])
        self.curve.set_xdata(logX)
        self.curve.set_ydata(LX)

    def reset_range(self):
        """ Reset the ranges of the higson plot. """
        xdata = self.curve.get_xdata()
        self.ax.set_xlim(max(xdata), min(xdata))


class Evolution(Slider):
    """ Slider controlling the evolution stage of the live points."""
    def __init__(self, fig, gridspec, action, valmax):
        super(Evolution, self).__init__(fig, gridspec, action, '',
                                        0, valmax, 0, 'horizontal')
        self.slider.valtext.set_horizontalalignment('right')
        self.slider.valtext.set_position((0.98, 0.5))

    def __call__(self):
        """ Return the current iteration as an integer. """
        mx = self.slider.valmax-1
        val = int(super(Evolution, self).__call__())
        return min(val, mx)

    def set_text(self, logL, n):
        """ Set the text at end of slider.

        Args:
            logL (float):
                Current loglikelihood of evolution stage

            n (float):
                Current number of live points of evolution stage
        """
        text = r'$\log L$: %.6g, $n_\mathrm{live}$: %i' % (logL, n)
        return super(Evolution, self).set_text(text)


class Temperature(Slider):
    """ Logarithmic slider controlling temperature of the posterior points."""
    def __init__(self, fig, gridspec, action):
        super(Temperature, self).__init__(fig, gridspec, action, r'$kT$',
                                          -1, 5, 0, 'vertical')

    def __call__(self):
        """ Return the current temperature. """
        return 10**super(Temperature, self).__call__()

    def set_text(self, kT):
        """ Set the text at end of slider.

        Args:
            kT (float):
                Current temperature of posterior points stage
        """
        text = r'%.2g' % kT
        return super(Temperature, self).set_text(text)


class RunPlotter(object):
    """ Construct a control panel of information on a nested sampling run.

    Args:
        root (str):
            The root string for the chains files to be used.

    Attributes:
        run (anesthetic.anesthetic.NestedSamples):
            Object for extracting nested sampling data from chains files.

        fig (matplotlib.figure.Figure):
            Reference to the underlying figure

        triangle (rhinestone.widgets.TrianglePlot):
            Corner plot of live or posterior samples.

        temperature (rhinestone.plot.Temperature):
            Slider selecting the posterior temperature.

        evolution (rhinestone.plot.Evolution):
            Slider selecting the live iteration.

        higson (rhinestone.plot.Higson):
            Higson plot of posterior weights.

        reset (rhinestone.widgets.Button):
            Button that resets the parameter ranges.

        reload (rhinestone.widgets.Button):
            Button that reloads the files.

        type (rhinestone.widgets.RadioButtons):
            Radio buttons that selects whether to plot live or posteriors.

        param_choice (rhinestone.widgets.CheckButtons):
            Checkbox that selects which parameters to plot.
    """
    def __init__(self, root, labels=None):
        self.run = NestedSamples.read(root)
        if labels is None:
            labels = self.run.paramnames[:10]

        self.labels = numpy.array(labels)
        self.fig = plt.figure()
        self._set_up()
        self.redraw(None)

    def _set_up(self):
        """ Draw the control panel.

        We implement the control panel using sequential recursive gridspecs.

        +----------------------------------------------+------+
        |                                              |      |
        |                  gs0[0]                      |gs0[1]|
        |                                              |      |
        |                                              |      |
        |                                              |      |
        |                                              |      |
        |                                              |      |
        |                                              |      |
        +-------------------------+-----------------+--+------+
        |                         |    gs11[0]      |         |
        |         gs10[0]         +-----------------+  gs1[2] |
        +-------------------------+    gs11[1]      |         |
        |                         +-----------------+         |
        |         gs10[1]         |    gs11[2]      |         |
        +-------------------------+-----------------+---------+

        These variable names are included in the __init__ function, and are
        named with an intuitive Huffman coding.
        """

        gs = GS(2, 1, height_ratios=[3, 1])
        gs0 = sGS(1, 2, width_ratios=[19, 1], subplot_spec=gs[0])
        gs1 = sGS(1, 3, width_ratios=[4, 1, 1], subplot_spec=gs[1])
        gs10 = sGS(2, 1, height_ratios=[1, 4], subplot_spec=gs1[0])
        gs11 = sGS(3, 1, height_ratios=[1, 1, 2], subplot_spec=gs1[1])

        self.triangle = TrianglePlot(self.fig, gs0[0])
        self.temperature = Temperature(self.fig, gs0[1], self.update)
        self.evolution = Evolution(self.fig, gs10[0],
                                   self.update, len(self.run))
        self.higson = Higson(self.fig, gs10[1])
        self.reset = Button(self.fig, gs11[0],
                            self.reset_range, 'Reset Range')
        self.reload = Button(self.fig, gs11[1],
                             self.reload_file, 'Reload File')
        self.type = RadioButtons(self.fig, gs11[2],
                                 ('live', 'posterior'), self.update)
        self.param_choice = CheckButtons(self.fig, gs1[2],
                                         self.labels, self.redraw)

    def redraw(self, _):
        """ Redraw the triangle plot upon parameter updating."""
        self.triangle.draw(self.param_choice())
        self.update(None)
        self.reset_range(None)
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def points(self, label):
        """ Get sample coordinates from nested sampling run.

        Args:
            label (str):
                label indicating the coordinate to extract.
        Returns:
            array(float):
                sample 'label'-coordinates.
        """
        if self.type() == 'posterior':
            kT = self.temperature()
            return self.run.posterior_points(1/kT)[label]
        else:
            i = self.evolution()
            logL = self.run.logL.iloc[i]
            return self.run.live_points(logL)[label]

    def update(self, _):
        """ Update all the plots upon slider changes."""
        logX = numpy.log(self.run.nlive/(self.run.nlive+1)).cumsum()
        kT = self.temperature()
        LX = self.run.logL/kT + logX
        LX = numpy.exp(LX-LX.max())
        i = self.evolution()
        logL = self.run.logL.iloc[i]
        try:
            n = self.run.nlive.iloc[i]
        except IndexError:
            n = 0

        self.triangle.update(self.points)

        self.evolution.set_text(logL, n)
        self.temperature.set_text(kT)

        self.higson.update(logX, LX, i)
        self.fig.canvas.draw()

    def reload_file(self, _):
        """ Reload the data from file."""
        self.run.reload_data()
        self.evolution.reset_range(valmax=self.run.npoints)
        self.update(None)

    def reset_range(self, _):
        """ Reset the parameter ranges. """
        self.triangle.reset_range()
        self.higson.reset_range()
        self.fig.canvas.draw()
