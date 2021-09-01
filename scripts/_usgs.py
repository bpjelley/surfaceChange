import matplotlib.cm as cm
import matplotlib.colors as colors

def _usgs(**kwargs):
    # set usgs RGB color data
    _usgs_data = {}
    _usgs_data['red'] = ((0.0, 0.4980392156862745, 0.4980392156862745),
        (0.048, 0.5098039215686274, 0.5098039215686274),
        (0.095, 0.6274509803921569, 0.6274509803921569),
        (0.143, 0.7254901960784313, 0.7254901960784313),
        (0.19, 0.8117647058823529, 0.8117647058823529),
        (0.238, 0.8745098039215686, 0.8745098039215686),
        (0.286, 0.9450980392156862, 0.9450980392156862),
        (0.333, 0.9294117647058824, 0.9294117647058824),
        (0.381, 0.9411764705882353, 0.9411764705882353),
        (0.429, 0.9019607843137255, 0.9019607843137255),
        (0.476, 0.8470588235294118, 0.8470588235294118),
        (0.524, 0.7725490196078432, 0.7725490196078432),
        (0.571, 0.8509803921568627, 0.8509803921568627),
        (0.619, 0.8901960784313725, 0.8901960784313725),
        (0.667, 0.8745098039215686, 0.8745098039215686),
        (0.714, 0.9372549019607843, 0.9372549019607843),
        (0.762, 0.9568627450980393, 0.9568627450980393),
        (0.81, 0.9529411764705882, 0.9529411764705882),
        (0.857, 0.9725490196078431, 0.9725490196078431),
        (0.905, 0.9725490196078431, 0.9725490196078431),
        (0.952, 0.9647058823529412, 0.9647058823529412),
        (1.0, 1.0, 1.0))
    _usgs_data['green'] = ((0.0, 0.6235294117647059, 0.6235294117647059),
        (0.048, 0.6901960784313725, 0.6901960784313725),
        (0.095, 0.7607843137254902, 0.7607843137254902),
        (0.143, 0.8392156862745098, 0.8392156862745098),
        (0.19, 0.8784313725490196, 0.8784313725490196),
        (0.238, 0.9137254901960784, 0.9137254901960784),
        (0.286, 0.9333333333333333, 0.9333333333333333),
        (0.333, 0.8745098039215686, 0.8745098039215686),
        (0.381, 0.8235294117647058, 0.8235294117647058),
        (0.429, 0.7372549019607844, 0.7372549019607844),
        (0.476, 0.6470588235294118, 0.6470588235294118),
        (0.524, 0.5843137254901961, 0.5843137254901961),
        (0.571, 0.6470588235294118, 0.6470588235294118),
        (0.619, 0.7176470588235294, 0.7176470588235294),
        (0.667, 0.7529411764705882, 0.7529411764705882),
        (0.714, 0.803921568627451, 0.803921568627451),
        (0.762, 0.8431372549019608, 0.8431372549019608),
        (0.81, 0.8745098039215686, 0.8745098039215686),
        (0.857, 0.8901960784313725, 0.8901960784313725),
        (0.905, 0.9137254901960784, 0.9137254901960784),
        (0.952, 0.9411764705882353, 0.9411764705882353),
        (1.0, 1.0, 1.0))
    _usgs_data['blue'] = ((0.0, 0.396078431372549, 0.396078431372549),
        (0.048, 0.4392156862745098, 0.4392156862745098),
        (0.095, 0.48627450980392156, 0.48627450980392156),
        (0.143, 0.48627450980392156, 0.48627450980392156),
        (0.19, 0.611764705882353, 0.611764705882353),
        (0.238, 0.6588235294117647, 0.6588235294117647),
        (0.286, 0.6509803921568628, 0.6509803921568628),
        (0.333, 0.6235294117647059, 0.6235294117647059),
        (0.381, 0.5529411764705883, 0.5529411764705883),
        (0.429, 0.5411764705882353, 0.5411764705882353),
        (0.476, 0.5215686274509804, 0.5215686274509804),
        (0.524, 0.5294117647058824, 0.5294117647058824),
        (0.571, 0.611764705882353, 0.611764705882353),
        (0.619, 0.6941176470588235, 0.6941176470588235),
        (0.667, 0.7490196078431373, 0.7490196078431373),
        (0.714, 0.8509803921568627, 0.8509803921568627),
        (0.762, 0.8823529411764706, 0.8823529411764706),
        (0.81, 0.9137254901960784, 0.9137254901960784),
        (0.857, 0.9098039215686274, 0.9098039215686274),
        (0.905, 0.9333333333333333, 0.9333333333333333),
        (0.952, 0.9607843137254902, 0.9607843137254902),
        (1.0, 1.0, 1.0))
    # create linear segmented colormap for usgs topography
    cmap = colors.LinearSegmentedColormap('usgs', _usgs_data, **kwargs)
    cmap.set_over('w')
    # register color map to be recognizable by cm.get_cmap()
    cm.register_cmap(name='usgs', cmap=cmap)
    # return the colormap
    return cmap
