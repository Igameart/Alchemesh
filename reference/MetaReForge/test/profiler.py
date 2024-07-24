import bpy
import cProfile
import pstats
import io

OUTPUT_FILE_PATH = "C:/temp/profiling_results.txt"

class MRF_ProfilerOperator(bpy.types.Operator):
    bl_idname = "object.simple_profiler"
    bl_label = "Simple Profiler"
    profiler = None

    def execute(self, context):
        if MRF_ProfilerOperator.profiler is None:
            # Starting Profile
            MRF_ProfilerOperator.profiler = cProfile.Profile()
            MRF_ProfilerOperator.profiler.enable()
            self.report({'INFO'}, "Profiler started")
        else:
            # Stopping profiler and writing stats
            MRF_ProfilerOperator.profiler.disable()
            s = io.StringIO()
            ps = pstats.Stats(MRF_ProfilerOperator.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats()
            
            with open(OUTPUT_FILE_PATH, 'w') as file:
                file.write(s.getvalue())
            self.report({'INFO'}, "Profiler stopped")
            MRF_ProfilerOperator.profiler = None

        return {'FINISHED'}

def register():
    bpy.utils.register_class(MRF_ProfilerOperator)

def unregister():
    bpy.utils.unregister_class(MRF_ProfilerOperator)
