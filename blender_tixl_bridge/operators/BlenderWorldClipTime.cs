using System.Runtime.InteropServices;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>
/// Preserves Blender's camera time mapping while allowing a world's clips to
/// adjust its animation independently through ordinary TiXL float operators.
/// </summary>
[Guid("a34b77c3-9eb5-41cd-86f6-6d8eba4fe0a0")]
public sealed class BlenderWorldClipTime : Instance<BlenderWorldClipTime>
{
    [Input(Guid = "784572bb-8070-4ebb-89e8-959caaaaff76")]
    public readonly InputSlot<float> GlobalClipTime = new();

    [Input(Guid = "ffef5b73-69cb-47f9-ae33-638d2659322b")]
    public readonly InputSlot<float> WorldClipTime = new();

    [Input(Guid = "375451d0-393d-49c4-9cf8-c2010c034894")]
    public readonly InputSlot<float> MappedSceneTime = new();

    [Input(Guid = "f67fb4a9-149c-4b49-84b8-f177bf653e9e")]
    public readonly InputSlot<bool> HasActiveWorldClip = new();

    [Output(Guid = "c1dbdb9e-a7ad-424b-b2ba-94bd9ce71daf", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<float> TimeSeconds = new();

    public BlenderWorldClipTime() => TimeSeconds.UpdateAction = Update;

    private void Update(EvaluationContext context)
    {
        var mapped = MappedSceneTime.GetValue(context);
        TimeSeconds.Value = HasActiveWorldClip.GetValue(context)
                                ? mapped + WorldClipTime.GetValue(context) - GlobalClipTime.GetValue(context)
                                : mapped;
    }
}
