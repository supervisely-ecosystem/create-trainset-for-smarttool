import supervisely_lib as sly

def validate_input_meta(meta: sly.ProjectMeta):
    classes_with_unsupported_shape = []
    for obj_class in meta.obj_classes:
        if obj_class.geometry_type != sly.Bitmap:
            classes_with_unsupported_shape.append((obj_class.name, obj_class.geometry_type.geometry_name()))

    if len(classes_with_unsupported_shape) > 0:
        raise TypeError('Unsupported shapes: {}. App supports only {}. '
                        'Use another apps to transform class shapes or rasterize objects. Learn more in app readme.'
                        .format(classes_with_unsupported_shape, sly.Bitmap.geometry_name()))


def modify_project_meta(meta: sly.ProjectMeta) -> sly.ProjectMeta:
    pass

def aug(image, ann: sly.Annotation):
    pass