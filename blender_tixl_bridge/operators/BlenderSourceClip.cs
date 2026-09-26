using System;
using System.Runtime.InteropServices;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>A timeline clip whose source range addresses seconds in a Blender export.</summary>
[Guid("622c47f1-a7f4-59ea-a9d0-9bd245842da3")]
public sealed class BlenderSourceClip : Instance<BlenderSourceClip>, IContentTimeClip
{
    [Output(Guid = "f6cf5a61-eae9-54cd-b02f-94b0a19d48f6", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly TimeClipSlot<float> TimeSeconds = new();

    public BlenderSourceClip()
    {
        TimeSeconds.UpdateAction = Update;
    }

    private void Update(EvaluationContext context)
    {
        // TimeClipSlot maps timeline bars into the clip's source range in seconds.
        TimeSeconds.Value = (float)context.LocalTime;
    }
}
