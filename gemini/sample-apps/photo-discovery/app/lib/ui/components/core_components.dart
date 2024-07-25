import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:flutter/services.dart';
import 'package:shimmer/shimmer.dart';

import '../../models/metadata.dart';

class TagCapsule extends StatelessWidget {
  const TagCapsule({
    required this.tags,
    this.title,
    required this.onTap,
    super.key,
  });

  final String? title;
  final List<String> tags;
  final Function(String text) onTap;

  @override
  Widget build(BuildContext context) {
    List<Widget> tagChips = [];

    for (int tagIndex = 0; tagIndex < tags.length; tagIndex++) {
      tagChips.addAll([
        ActionChip(
          label: Text(tags[tagIndex]),
          onPressed: () => onTap(tags[tagIndex]),
          backgroundColor: Theme.of(context).colorScheme.secondaryContainer,
        ),
        const SizedBox.square(
          dimension: 8,
        ),
      ]);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (title != null)
          Text(
            title!,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.secondary,
            ),
          ),
        SizedBox(
          height: 50,
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: tagChips,
          ),
        ),
      ],
    );
  }
}

class TextCapsule extends StatelessWidget {
  const TextCapsule({
    required this.title,
    required this.content,
    this.enableCopy = false,
    this.loading = false,
    this.shimmerHeight = 60,
    super.key,
  });

  final String title;
  final String content;
  final bool enableCopy;
  final bool loading;
  final double shimmerHeight;

  void copyText() async {
    await Clipboard.setData(
      ClipboardData(
        text: content,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.secondary,
            fontSize: 18,
          ),
        ),
        loading
            ? LayoutBuilder(
                builder: (context, constraints) => Shimmer.fromColors(
                  period: const Duration(seconds: 3),
                  baseColor: Theme.of(context).colorScheme.surfaceContainer,
                  highlightColor:
                      Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8),
                      color: Theme.of(context).colorScheme.surface,
                    ),
                    width: constraints.maxWidth,
                    height: shimmerHeight,
                  ),
                ),
              )
            : ListTile(
                title: Text(
                  content,
                  style: const TextStyle(
                    fontSize: 18,
                  ),
                ),
                trailing: enableCopy
                    ? IconButton(
                        icon: const Icon(FontAwesomeIcons.copy),
                        onPressed: copyText,
                      )
                    : null,
              ),
      ],
    );
  }
}

class MetadataCard extends StatelessWidget {
  const MetadataCard(
      {required this.metadata, required this.loading, super.key});

  final bool loading;
  final Metadata? metadata;

  @override
  Widget build(BuildContext context) {
    var localMetadata = metadata;

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox.square(
            dimension: 16,
          ),
          TextCapsule(
            title: 'Name',
            content: localMetadata == null ? '' : localMetadata.name,
            enableCopy: true,
            loading: loading,
          ),
          const SizedBox.square(
            dimension: 16,
          ),
          TextCapsule(
            title: 'Description',
            content: localMetadata == null ? '' : localMetadata.description,
            loading: loading,
            shimmerHeight: 80,
          ),
        ]),
      ),
    );
  }
}
